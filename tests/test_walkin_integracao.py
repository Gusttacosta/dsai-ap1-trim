"""
Testes de integração da fila de espera (walk-in) (#3).

Spec: SPEC/2026-11-24-testes-integracao-walkin.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. O "hoje" do serviço é fixado no `current_date` do banco, para a fila não
depender do fuso de quem roda os testes. Substituem o tests/test_walkin.py gerado, que não importava
a aplicação.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.auth.models import UserRole
from src.backend.modules.walkin import service as walkin_service
from src.backend.modules.walkin.models import WalkInQueue, WalkInStatus
from tests.agenda_fixtures import count, create_shop, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/queue"
NOT_IN_QUEUE = "Registro na fila não encontrado."
ONLY_WAITING = "Apenas registros aguardando podem ser cancelados."


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def shop(sessionmaker, monkeypatch):
    """Barbearia de create_shop (corte de 30 min a 40,00) com o "hoje" da fila igual ao do banco."""
    async with sessionmaker() as db:
        db_today = (await db.execute(text("select current_date"))).scalar_one()

    class FixedDate(date):
        @classmethod
        def today(cls):
            return db_today

    monkeypatch.setattr(walkin_service, "date", FixedDate)
    return await create_shop(sessionmaker)


async def join(client, user, shop, name="João Silva", **extra):
    body = {"customer_name": name, "requested_service_id": str(shop["service_id"]), **extra}
    response = await client.post(URL, json=body, headers=auth(user))
    assert response.status_code == 201, response.text
    return response.json()


async def assign(client, user, walkin_id, barber_id):
    return await client.put(f"{URL}/{walkin_id}/assign", json={"barber_id": str(barber_id)}, headers=auth(user))


async def cancel(client, user, walkin_id):
    return await client.put(f"{URL}/{walkin_id}/cancel", headers=auth(user))


async def live(client):
    response = await client.get(f"{URL}/live")
    assert response.status_code == 200, response.text
    return response.json()


async def walkin_in_db(maker, walkin_id):
    async with maker() as db:
        return await db.get(WalkInQueue, uuid.UUID(str(walkin_id)))


async def appointments_in_db(maker):
    async with maker() as db:
        return list((await db.execute(select(Appointment))).scalars().all())


# ── entrar na fila ──────────────────────────────────────


async def test_join_puts_the_customer_waiting_at_the_end(client, shop, sessionmaker):
    barber_user = shop["barber_user"]
    first = await join(client, barber_user, shop, "João Silva")
    assert first["status"] == "waiting"
    assert first["position"] == 1
    assert first["customer_name"] == "João Silva"
    assert first["requested_service_id"] == str(shop["service_id"])
    assert first["requested_barber_id"] is None
    assert first["user_id"] is None
    assert first["joined_at"]
    assert first["finished_at"] is None

    second = await join(
        client, barber_user, shop, "Ana Souza", user_id=str(shop["client"].id), requested_barber_id=str(shop["barber_id"])
    )
    assert second["position"] == 2
    assert (second["user_id"], second["requested_barber_id"]) == (str(shop["client"].id), str(shop["barber_id"]))
    saved = await walkin_in_db(sessionmaker, second["id"])
    assert (saved.status, saved.position, saved.customer_name) == (WalkInStatus.WAITING, 2, "Ana Souza")


async def test_positions_keep_counting_after_people_leave(client, shop):
    staff = shop["barber_user"]
    first = await join(client, staff, shop, "Ana")
    second = await join(client, staff, shop, "Bia", user_id=str(shop["client"].id))
    assert (await cancel(client, staff, first["id"])).status_code == 200
    assert (await assign(client, staff, second["id"], shop["barber_id"])).status_code == 200
    third = await join(client, staff, shop, "Caio")
    assert third["position"] == 3


async def test_yesterdays_queue_does_not_count(client, shop, sessionmaker):
    async with sessionmaker() as db:
        db.add(WalkInQueue(
            customer_name="Ontem", requested_service_id=shop["service_id"], position=7,
            joined_at=datetime.now(timezone.utc) - timedelta(days=2),
        ))
        await db.commit()
    first = await join(client, shop["barber_user"], shop, "Hoje")
    assert first["position"] == 1
    assert [p["customer_name_masked"] for p in await live(client)] == ["Hoj***"]


@pytest.mark.parametrize(
    "change", [{"customer_name": "x" * 151}, {"customer_name": None}, {"requested_service_id": None},
               {"requested_service_id": "nao-e-uuid"}]
)
async def test_invalid_join_gets_422(client, shop, sessionmaker, change):
    body = {"customer_name": "João", "requested_service_id": str(shop["service_id"])}
    body.update(change)
    body = {k: v for k, v in body.items() if v is not None}
    response = await client.post(URL, json=body, headers=auth(shop["barber_user"]))
    assert response.status_code == 422
    assert await count(sessionmaker, WalkInQueue) == 0


# ── fila ao vivo ────────────────────────────────────────


async def test_live_queue_masks_names_in_position_order(client, shop):
    staff = shop["barber_user"]
    await join(client, staff, shop, "João Silva")
    await join(client, staff, shop, "Li Wu")
    await join(client, staff, shop, "Beatriz de Souza")

    body = await live(client)
    assert [(p["customer_name_masked"], p["position"]) for p in body] == [
        ("Joã***", 1), ("Li***", 2), ("Bea***", 3),
    ]
    assert all(set(p) == {"customer_name_masked", "position", "joined_at"} for p in body)


async def test_live_queue_shows_only_who_is_waiting(client, shop):
    staff = shop["barber_user"]
    attended = await join(client, staff, shop, "Ana Lima", user_id=str(shop["client"].id))
    gave_up = await join(client, staff, shop, "Bia Reis")
    await join(client, staff, shop, "Caio Melo")
    assert (await assign(client, staff, attended["id"], shop["barber_id"])).status_code == 200
    assert (await cancel(client, staff, gave_up["id"])).status_code == 200

    assert [(p["customer_name_masked"], p["position"]) for p in await live(client)] == [("Cai***", 3)]


async def test_empty_live_queue(client, shop):
    assert await live(client) == []


# ── puxar para a cadeira ────────────────────────────────


async def test_assign_starts_an_appointment_for_the_customer(client, shop, sessionmaker):
    staff = shop["barber_user"]
    walkin = await join(client, staff, shop, "Ana Lima", user_id=str(shop["client"].id))
    before = datetime.now(timezone.utc)

    response = await assign(client, staff, walkin["id"], shop["barber_id"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "attending"
    assert body["finished_at"]

    [appointment] = await appointments_in_db(sessionmaker)
    assert appointment.client_id == shop["client"].id
    assert appointment.barber_id == shop["barber_id"]
    assert appointment.status == AppointmentStatus.CONFIRMED
    assert Decimal(appointment.total_price) == Decimal("40.00")
    assert before - timedelta(seconds=5) <= appointment.start_datetime <= datetime.now(timezone.utc)
    assert (await walkin_in_db(sessionmaker, walkin["id"])).status == WalkInStatus.ATTENDING


async def test_admin_can_assign_to_any_barber(client, shop, sessionmaker):
    admin = await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)
    walkin = await join(client, admin, shop, "Ana Lima", user_id=str(shop["client"].id))
    assert (await assign(client, admin, walkin["id"], shop["barber_id"])).status_code == 200
    [appointment] = await appointments_in_db(sessionmaker)
    assert appointment.barber_id == shop["barber_id"]


async def test_assign_uses_the_barber_informed_at_the_chair(client, shop, sessionmaker):
    asked = await add_barber(sessionmaker, "pedido@teste.com")
    walkin = await join(
        client, shop["barber_user"], shop, "Ana Lima", user_id=str(shop["client"].id), requested_barber_id=str(asked.id)
    )
    assert (await assign(client, shop["barber_user"], walkin["id"], shop["barber_id"])).status_code == 200
    [appointment] = await appointments_in_db(sessionmaker)
    assert appointment.barber_id == shop["barber_id"]


@pytest.mark.parametrize("first", ["assign", "cancel"])
async def test_assign_only_from_waiting(client, shop, sessionmaker, first):
    staff = shop["barber_user"]
    walkin = await join(client, staff, shop, "Ana Lima", user_id=str(shop["client"].id))
    if first == "assign":
        await assign(client, staff, walkin["id"], shop["barber_id"])
        status = "attending"
    else:
        await cancel(client, staff, walkin["id"])
        status = "cancelled"
    appointments_before = await count(sessionmaker, Appointment)

    response = await assign(client, staff, walkin["id"], shop["barber_id"])
    assert response.status_code == 400
    assert response.json()["detail"] == f"Este registro já está com status {status}."
    assert await count(sessionmaker, Appointment) == appointments_before


async def test_assign_unknown_walkin_gets_400(client, shop, sessionmaker):
    response = await assign(client, shop["barber_user"], uuid.uuid4(), shop["barber_id"])
    assert response.status_code == 400
    assert response.json()["detail"] == NOT_IN_QUEUE
    assert await count(sessionmaker, Appointment) == 0


async def test_assign_without_barber_gets_422(client, shop):
    walkin = await join(client, shop["barber_user"], shop, user_id=str(shop["client"].id))
    response = await client.put(f"{URL}/{walkin['id']}/assign", json={}, headers=auth(shop["barber_user"]))
    assert response.status_code == 422


# ── cancelar ────────────────────────────────────────────


async def test_cancel_marks_the_customer_as_gone(client, shop, sessionmaker):
    walkin = await join(client, shop["barber_user"], shop)
    response = await cancel(client, shop["barber_user"], walkin["id"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["finished_at"]
    assert (await walkin_in_db(sessionmaker, walkin["id"])).status == WalkInStatus.CANCELLED
    assert await count(sessionmaker, Appointment) == 0


@pytest.mark.parametrize("first", ["assign", "cancel"])
async def test_cancel_only_while_waiting(client, shop, sessionmaker, first):
    staff = shop["barber_user"]
    walkin = await join(client, staff, shop, "Ana Lima", user_id=str(shop["client"].id))
    if first == "assign":
        await assign(client, staff, walkin["id"], shop["barber_id"])
    else:
        await cancel(client, staff, walkin["id"])
    response = await cancel(client, staff, walkin["id"])
    assert response.status_code == 400
    assert response.json()["detail"] == ONLY_WAITING
    expected = WalkInStatus.ATTENDING if first == "assign" else WalkInStatus.CANCELLED
    assert (await walkin_in_db(sessionmaker, walkin["id"])).status == expected


async def test_cancel_unknown_walkin_gets_400(client, shop):
    response = await cancel(client, shop["barber_user"], uuid.uuid4())
    assert response.status_code == 400
    assert response.json()["detail"] == NOT_IN_QUEUE


# ── permissões ──────────────────────────────────────────


@pytest.mark.parametrize("who", [None, "client"])
async def test_staff_routes_are_forbidden_to_others(client, shop, sessionmaker, who):
    walkin = await join(client, shop["barber_user"], shop, user_id=str(shop["client"].id))
    headers = auth(shop[who]) if who else {}
    body = {"customer_name": "Intruso", "requested_service_id": str(shop["service_id"])}
    responses = [
        await client.post(URL, json=body, headers=headers),
        await client.put(f"{URL}/{walkin['id']}/assign", json={"barber_id": str(shop["barber_id"])}, headers=headers),
        await client.put(f"{URL}/{walkin['id']}/cancel", headers=headers),
    ]
    assert [r.status_code for r in responses] == [403, 403, 403]
    assert await count(sessionmaker, WalkInQueue) == 1
    assert (await walkin_in_db(sessionmaker, walkin["id"])).status == WalkInStatus.WAITING
    assert await count(sessionmaker, Appointment) == 0


async def test_live_queue_is_public(client, shop):
    await join(client, shop["barber_user"], shop, "João Silva")
    assert [p["customer_name_masked"] for p in await live(client)] == ["Joã***"]
