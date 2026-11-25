"""
Notificações: avisos de agendamento, aviso geral só para contas ativas e com público, textos
vazios, paginação e exclusão (#75).

Spec: SPEC/2026-11-25-notificacoes.md
"""

import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.appointments.models import Appointment
from src.backend.modules.appointments.models import AppointmentStatus as S
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.notifications.models import Notification, NotificationType
from tests.agenda_fixtures import brt, count, create_shop, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/notifications"
NOW = brt(2026, 12, 1, 8, 0)
DAY = date(2026, 12, 2)


@pytest_asyncio.fixture
async def shop(sessionmaker, set_now):
    set_now(NOW)
    return await create_shop(sessionmaker)


async def inbox(maker, user_id):
    async with maker() as db:
        rows = await db.execute(
            select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at)
        )
        return [(n.title, n.message, n.type) for n in rows.scalars().all()]


async def book(client, shop, hour=10):
    body = {
        "barber_id": str(shop["barber_id"]),
        "start_datetime": f"{DAY.isoformat()}T{hour:02d}:00:00",
        "service_ids": [str(shop["service_id"])],
    }
    response = await client.post("/api/appointments", json=body, headers=auth(shop["client"]))
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ── item 1: avisos de agendamento ───────────────────────


async def test_booking_notifies_client_and_barber(client, shop, sessionmaker):
    await book(client, shop)

    kind = NotificationType.APPOINTMENT_REMINDER
    assert await inbox(sessionmaker, shop["client"].id) == [
        ("Agendamento recebido", "Seu horário de 02/12 às 10:00 foi registrado.", kind)
    ]
    assert await inbox(sessionmaker, shop["barber_user"].id) == [
        ("Novo agendamento", "Você tem um novo horário em 02/12 às 10:00.", kind)
    ]


async def test_refused_booking_notifies_nobody(client, shop, sessionmaker):
    await book(client, shop)
    body = {
        "barber_id": str(shop["barber_id"]),
        "start_datetime": f"{DAY.isoformat()}T10:00:00",
        "service_ids": [str(shop["service_id"])],
    }
    assert (await client.post("/api/appointments", json=body, headers=auth(shop["client"]))).status_code == 400
    assert await count(sessionmaker, Notification) == 2


async def test_guest_booking_does_not_notify_the_ghost(client, shop, sessionmaker):
    body = {
        "barber_id": str(shop["barber_id"]),
        "start_datetime": f"{DAY.isoformat()}T11:00:00",
        "service_ids": [str(shop["service_id"])],
        "guest_name": "Ana Souza",
    }
    response = await client.post("/api/appointments/guest", json=body)
    assert response.status_code == 201, response.text
    client_id = uuid.UUID(response.json()["client_id"])
    async with sessionmaker() as db:
        guest = await db.get(User, client_id)
    # Até o PR da #21, o visitante é um usuário fantasma ativo; depois, o Visitante inativo.
    expected = 1 if guest.is_active else 0
    assert len(await inbox(sessionmaker, client_id)) == expected
    assert [t for t, _, _ in await inbox(sessionmaker, shop["barber_user"].id)] == ["Novo agendamento"]


async def pending_booking(maker, shop):
    """Agendamento pendente (o da rota já nasce confirmado)."""
    async with maker() as db:
        start = brt(2026, 12, 2, 15, 0)
        appointment = Appointment(
            client_id=shop["client"].id, barber_id=shop["barber_id"], start_datetime=start,
            end_datetime=start + timedelta(minutes=30), status=S.PENDING, total_price=40,
        )
        db.add(appointment)
        await db.commit()
        return appointment.id


async def change(client, shop, appointment_id, status):
    response = await client.put(
        f"/api/appointments/{appointment_id}/status", json={"status": status}, headers=auth(shop["barber_user"]),
    )
    assert response.status_code == 200, response.text


async def test_confirming_notifies_the_client(client, shop, sessionmaker):
    await change(client, shop, await pending_booking(sessionmaker, shop), "confirmed")
    assert await inbox(sessionmaker, shop["client"].id) == [
        ("Agendamento confirmado", "Seu horário de 02/12 às 15:00 foi confirmado.", NotificationType.APPOINTMENT_REMINDER)
    ]


async def test_cancelling_by_the_shop_notifies_the_client(client, shop, sessionmaker):
    appointment_id = await book(client, shop)
    await change(client, shop, appointment_id, "cancelled")
    titles = [t for t, _, _ in await inbox(sessionmaker, shop["client"].id)]
    assert titles == ["Agendamento recebido", "Agendamento cancelado"]


async def test_completed_appointment_thanks_the_client(client, shop, sessionmaker, set_now):
    appointment_id = await book(client, shop)
    set_now(brt(2026, 12, 2, 10, 15))
    await change(client, shop, appointment_id, "completed")
    titles = [t for t, _, _ in await inbox(sessionmaker, shop["client"].id)]
    # Os pontos do atendimento (#13) chegam no mesmo commit: a ordem entre os dois não é fixa.
    assert titles[0] == "Agendamento recebido"
    assert sorted(titles[1:]) == ["Atendimento concluído", "Você ganhou pontos"]


async def test_client_cancellation_notifies_the_barber(client, shop, sessionmaker):
    appointment_id = await book(client, shop)
    response = await client.put(f"/api/appointments/{appointment_id}/cancel", headers=auth(shop["client"]))
    assert response.status_code == 200, response.text
    titles = [t for t, _, _ in await inbox(sessionmaker, shop["barber_user"].id)]
    assert titles == ["Novo agendamento", "Agendamento cancelado"]


async def test_inactive_client_gets_no_notice(client, shop, sessionmaker):
    async with sessionmaker() as db:
        start = brt(2026, 12, 2, 15, 0)
        appointment = Appointment(
            client_id=shop["client"].id, barber_id=shop["barber_id"], start_datetime=start,
            end_datetime=start + timedelta(minutes=30), status=S.PENDING, total_price=40,
        )
        db.add(appointment)
        (await db.get(User, shop["client"].id)).is_active = False
        await db.commit()
    url = f"/api/appointments/{appointment.id}/status"
    assert (await client.put(url, json={"status": "confirmed"}, headers=auth(shop["barber_user"]))).status_code == 200
    assert await inbox(sessionmaker, shop["client"].id) == []


# ── item 2: aviso geral ─────────────────────────────────


@pytest_asyncio.fixture
async def people(sessionmaker):
    admin = await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)
    ana = await add_user(sessionmaker, "ana@teste.com")
    gone = await add_user(sessionmaker, "saiu@teste.com", is_active=False)
    barber = await add_barber(sessionmaker, "bia@teste.com")
    return {"admin": admin, "ana": ana, "gone": gone, "barber_user_id": barber.user_id}


async def broadcast(client, admin, **body):
    return await client.post(f"{URL}/broadcast", json={"title": "Feriado", "message": "Fechados.", **body},
                             headers=auth(admin))


async def recipients(maker):
    async with maker() as db:
        return set((await db.execute(select(Notification.user_id))).scalars().all())


async def test_broadcast_skips_deactivated_accounts(client, sessionmaker, people):
    response = await broadcast(client, people["admin"])
    assert response.json() == {"detail": "Mensagem enviada para 3 usuários."}
    assert people["gone"].id not in await recipients(sessionmaker)


@pytest.mark.parametrize(
    "audience, who",
    [("clients", ["ana"]), ("barbers", ["barber_user_id"]), ("admins", ["admin"]), ("all", ["admin", "ana", "barber_user_id"])],
)
async def test_broadcast_audience(client, sessionmaker, people, audience, who):
    assert (await broadcast(client, people["admin"], audience=audience)).status_code == 201
    expected = {people[w] if w == "barber_user_id" else people[w].id for w in who}
    assert await recipients(sessionmaker) == expected


@pytest.mark.parametrize(
    "body", [{"title": "", "message": "m"}, {"title": "   ", "message": "m"}, {"title": "t", "message": ""},
             {"title": "t", "message": "  "}, {"title": "t", "message": "m", "audience": "todos"}],
)
async def test_blank_or_invalid_broadcast_gets_422(client, sessionmaker, people, body):
    response = await client.post(f"{URL}/broadcast", json=body, headers=auth(people["admin"]))
    assert response.status_code == 422
    assert await count(sessionmaker, Notification) == 0


# ── item 4: paginação e exclusão ────────────────────────


async def fill(maker, user, n, read_every=None):
    async with maker() as db:
        for i in range(n):
            db.add(Notification(
                user_id=user.id, title=f"Aviso {i:02d}", message="m", type=NotificationType.SYSTEM_ALERT,
                is_read=bool(read_every and i % read_every == 0),
            ))
            await db.flush()
        await db.commit()


async def test_list_is_paginated(client, sessionmaker):
    user = await add_user(sessionmaker, "ana@teste.com")
    await fill(sessionmaker, user, 60)
    first = (await client.get(URL, headers=auth(user))).json()
    assert len(first) == 50
    page = (await client.get(URL, params={"limit": 20, "offset": 50}, headers=auth(user))).json()
    assert len(page) == 10
    assert not {n["id"] for n in first} & {n["id"] for n in page}


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"offset": -1}])
async def test_invalid_page_gets_422(client, sessionmaker, params):
    user = await add_user(sessionmaker, "ana@teste.com")
    assert (await client.get(URL, params=params, headers=auth(user))).status_code == 422


async def test_unread_only(client, sessionmaker):
    user = await add_user(sessionmaker, "ana@teste.com")
    await fill(sessionmaker, user, 6, read_every=2)
    body = (await client.get(URL, params={"unread_only": True}, headers=auth(user))).json()
    assert len(body) == 3 and all(not n["is_read"] for n in body)


async def test_delete_own_notification(client, sessionmaker):
    user = await add_user(sessionmaker, "ana@teste.com")
    await fill(sessionmaker, user, 2)
    [first, second] = (await client.get(URL, headers=auth(user))).json()

    assert (await client.delete(f"{URL}/{first['id']}", headers=auth(user))).status_code == 204

    assert [n["id"] for n in (await client.get(URL, headers=auth(user))).json()] == [second["id"]]


async def test_cannot_delete_someone_elses_or_unknown(client, sessionmaker):
    ana = await add_user(sessionmaker, "ana@teste.com")
    bia = await add_user(sessionmaker, "bia@teste.com")
    await fill(sessionmaker, ana, 1)
    [mine] = (await client.get(URL, headers=auth(ana))).json()
    for target in (mine["id"], str(uuid.uuid4())):
        response = await client.delete(f"{URL}/{target}", headers=auth(bia))
        assert response.status_code == 404
        assert response.json()["detail"] == "Notificação não encontrada."
    assert await count(sessionmaker, Notification) == 1
