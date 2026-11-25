"""
Cliente sem conta na fila de espera e no agendamento de visitante (#21 e #69).

Spec: SPEC/2026-11-25-cliente-sem-conta.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`).
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from src.backend.modules.appointments.models import Appointment, AppointmentItem
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber
from src.backend.modules.services.models import Service
from src.backend.modules.walkin import service as walkin_service
from src.backend.modules.walkin.models import WalkInQueue, WalkInStatus
from tests.agenda_fixtures import count, create_shop, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/queue"
BRT = ZoneInfo("America/Sao_Paulo")
VISITOR = "visitante@trim.local"


@pytest_asyncio.fixture
async def shop(sessionmaker):
    return await create_shop(sessionmaker)


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


async def join(client, user, shop, name="João Silva", **extra):
    body = {"customer_name": name, "requested_service_id": str(shop["service_id"]), **extra}
    return await client.post(URL, json=body, headers=auth(user))


async def joined(client, user, shop, name="João Silva", **extra):
    response = await join(client, user, shop, name, **extra)
    assert response.status_code == 201, response.text
    return response.json()


async def assign(client, user, walkin_id, barber_id):
    return await client.put(f"{URL}/{walkin_id}/assign", json={"barber_id": str(barber_id)}, headers=auth(user))


async def only_appointment(maker):
    async with maker() as db:
        [appointment] = (await db.execute(select(Appointment))).scalars().all()
        items = (await db.execute(select(AppointmentItem))).scalars().all()
        return appointment, list(items)


# ── item 1: cliente sem conta vai para a cadeira ────────


async def test_walkin_without_account_is_assigned_to_the_visitor(client, shop, sessionmaker):
    walkin = await joined(client, shop["barber_user"], shop, "Carlos Souza")

    response = await assign(client, shop["barber_user"], walkin["id"], shop["barber_id"])

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "attending"
    appointment, _ = await only_appointment(sessionmaker)
    async with sessionmaker() as db:
        visitor = await db.get(User, appointment.client_id)
    assert (visitor.email, visitor.is_active) == (VISITOR, False)
    assert appointment.notes == "Fila de espera: Carlos Souza"


async def test_two_walkins_without_account_share_the_visitor(client, shop, sessionmaker):
    staff = shop["barber_user"]
    second_barber = await add_barber(sessionmaker, "bia@teste.com")
    async with sessionmaker() as db:
        bia = await db.get(User, second_barber.user_id)
    first = await joined(client, staff, shop, "Carlos")
    second = await joined(client, staff, shop, "Davi")
    assert (await assign(client, staff, first["id"], shop["barber_id"])).status_code == 200
    assert (await assign(client, bia, second["id"], second_barber.id)).status_code == 200

    async with sessionmaker() as db:
        visitors = (await db.execute(select(User).where(User.email == VISITOR))).scalars().all()
        clients = (await db.execute(select(Appointment.client_id))).scalars().all()
    assert len(visitors) == 1
    assert set(clients) == {visitors[0].id}


async def test_walkin_with_account_keeps_its_client(client, shop, sessionmaker):
    walkin = await joined(client, shop["barber_user"], shop, "Ana", user_id=str(shop["client"].id))
    assert (await assign(client, shop["barber_user"], walkin["id"], shop["barber_id"])).status_code == 200
    appointment, _ = await only_appointment(sessionmaker)
    assert appointment.client_id == shop["client"].id
    assert await count(sessionmaker, User) == 2  # nenhum Visitante criado


# ── item 4: agendamento completo ────────────────────────


async def test_assigned_appointment_has_the_service_duration_and_item(client, shop, sessionmaker):
    walkin = await joined(client, shop["barber_user"], shop)
    assert (await assign(client, shop["barber_user"], walkin["id"], shop["barber_id"])).status_code == 200

    appointment, items = await only_appointment(sessionmaker)
    assert appointment.end_datetime - appointment.start_datetime == timedelta(minutes=30)
    assert Decimal(appointment.total_price) == Decimal("40.00")
    [item] = items
    assert (item.service_id, item.service_name, item.duration_minutes) == (shop["service_id"], "Corte", 30)
    assert Decimal(item.locked_price) == Decimal("40.00")


async def test_barber_cannot_pull_customer_to_another_barbers_chair(client, shop, sessionmaker):
    other = await add_barber(sessionmaker, "bia@teste.com")
    walkin = await joined(client, shop["barber_user"], shop)

    response = await assign(client, shop["barber_user"], walkin["id"], other.id)

    assert response.status_code == 403
    assert response.json()["detail"] == "O barbeiro só pode puxar o cliente para a própria cadeira."
    assert await count(sessionmaker, Appointment) == 0
    async with sessionmaker() as db:
        assert (await db.get(WalkInQueue, uuid.UUID(walkin["id"]))).status == WalkInStatus.WAITING


async def test_admin_pulls_to_any_chair(client, shop, sessionmaker, admin):
    other = await add_barber(sessionmaker, "bia@teste.com")
    walkin = await joined(client, admin, shop)
    assert (await assign(client, admin, walkin["id"], other.id)).status_code == 200
    appointment, _ = await only_appointment(sessionmaker)
    assert appointment.barber_id == other.id


async def test_barber_user_without_profile_cannot_assign(client, shop, sessionmaker):
    no_profile = await add_user(sessionmaker, "sem.perfil@teste.com", UserRole.BARBER)
    walkin = await joined(client, shop["barber_user"], shop)
    response = await assign(client, no_profile, walkin["id"], shop["barber_id"])
    assert response.status_code == 403
    assert await count(sessionmaker, Appointment) == 0


# ── item 2: nome só com espaços ─────────────────────────


@pytest.mark.parametrize("name", ["", "   ", "\t"])
async def test_blank_name_gets_422(client, shop, sessionmaker, name):
    assert (await join(client, shop["barber_user"], shop, name)).status_code == 422
    assert await count(sessionmaker, WalkInQueue) == 0


async def test_name_is_trimmed(client, shop):
    assert (await joined(client, shop["barber_user"], shop, "  Ana Lima  "))["customer_name"] == "Ana Lima"


async def test_live_queue_survives_an_old_blank_name(client, shop, sessionmaker):
    async with sessionmaker() as db:
        db.add(WalkInQueue(customer_name="   ", requested_service_id=shop["service_id"], position=1))
        await db.commit()
    response = await client.get(f"{URL}/live")
    assert response.status_code == 200
    assert [p["customer_name_masked"] for p in response.json()] == ["?***"]


# ── item 3: IDs desconhecidos ───────────────────────────


@pytest.mark.parametrize(
    "field, detail",
    [
        ("requested_service_id", "Serviço não encontrado ou inativo."),
        ("requested_barber_id", "Barbeiro não encontrado ou inativo."),
        ("user_id", "Cliente não encontrado."),
    ],
)
async def test_unknown_ids_on_join_get_404(client, shop, sessionmaker, field, detail):
    response = await join(client, shop["barber_user"], shop, **{field: str(uuid.uuid4())})
    assert response.status_code == 404
    assert response.json()["detail"] == detail
    assert await count(sessionmaker, WalkInQueue) == 0


async def test_inactive_service_on_join_gets_404(client, shop, sessionmaker):
    async with sessionmaker() as db:
        await db.execute(update(Service).values(is_active=False))
        await db.commit()
    assert (await join(client, shop["barber_user"], shop)).status_code == 404


@pytest.mark.parametrize("barber", ["desconhecido", "desativado"])
async def test_unknown_or_inactive_barber_on_assign_gets_404(client, shop, sessionmaker, admin, barber):
    walkin = await joined(client, admin, shop)
    if barber == "desconhecido":
        barber_id = uuid.uuid4()
    else:
        other = await add_barber(sessionmaker, "bia@teste.com")
        async with sessionmaker() as db:
            await db.execute(update(Barber).where(Barber.id == other.id).values(is_active=False))
            await db.commit()
        barber_id = other.id

    response = await assign(client, admin, walkin["id"], barber_id)

    assert response.status_code == 404
    assert response.json()["detail"] == "Barbeiro não encontrado ou inativo."
    assert await count(sessionmaker, Appointment) == 0


# ── item 5: o dia da fila é o da barbearia ──────────────


async def test_queue_day_follows_the_shop_timezone(client, shop, sessionmaker, monkeypatch):
    """Às 22:00 em Brasília o servidor em UTC já está no dia seguinte; a fila não pode virar."""
    now = datetime(2026, 11, 25, 22, 0, tzinfo=BRT)
    monkeypatch.setattr(walkin_service, "utc_now", lambda: now.astimezone(timezone.utc))
    async with sessionmaker() as db:
        db.add_all([
            # 20:00 de 25/11 em Brasília (23:00Z): mesmo dia da barbearia.
            WalkInQueue(customer_name="Cedo", requested_service_id=shop["service_id"], position=1,
                        joined_at=datetime(2026, 11, 25, 20, 0, tzinfo=BRT)),
            # 23:30 de 24/11 em Brasília (02:30Z de 25/11): dia anterior, mesmo com a data UTC de 25.
            WalkInQueue(customer_name="Ontem", requested_service_id=shop["service_id"], position=9,
                        joined_at=datetime(2026, 11, 24, 23, 30, tzinfo=BRT)),
        ])
        await db.commit()

    live = (await client.get(f"{URL}/live")).json()
    assert [p["customer_name_masked"] for p in live] == ["Ced***"]
    assert (await joined(client, shop["barber_user"], shop, "Tarde"))["position"] == 2


# ── #21: agendamento de visitante ───────────────────────


async def test_guest_route_reuses_the_visitor_across_bookings(client, shop, sessionmaker):
    start = (datetime.now(BRT) + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
    for hour in (10, 11):
        body = {
            "barber_id": str(shop["barber_id"]),
            "start_datetime": start.replace(hour=hour).strftime("%Y-%m-%dT%H:%M:%S"),
            "service_ids": [str(shop["service_id"])],
            "guest_name": "Ana Souza",
        }
        response = await client.post("/api/appointments/guest", json=body)
        assert response.status_code == 201, response.text
    async with sessionmaker() as db:
        users = (await db.execute(select(User.email))).scalars().all()
    assert sorted(users) == sorted(["cliente@teste.com", "barbeiro@teste.com", VISITOR])


@pytest.mark.parametrize("password", ["", "senha123", "!sem-login!"])
async def test_visitor_cannot_log_in(client, shop, sessionmaker, password):
    walkin = await joined(client, shop["barber_user"], shop)
    assert (await assign(client, shop["barber_user"], walkin["id"], shop["barber_id"])).status_code == 200

    response = await client.post("/api/auth/login", json={"email": VISITOR, "password": password})
    assert response.status_code != 200
    assert "access_token" not in response.text
