"""
Testes de integração das notificações (#3).

Spec: SPEC/2026-11-24-testes-integracao-notifications.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. O `create_notification`, que não tem rota, é testado direto pelo serviço.
Substituem o tests/test_notifications.py gerado, que não importava a aplicação.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.auth.models import UserRole
from src.backend.modules.notifications.models import Notification, NotificationType
from src.backend.modules.notifications.schemas import NotificationCreateRequest
from src.backend.modules.notifications.service import NotificationService
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/notifications"
BASE = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def member(sessionmaker):
    return await add_user(sessionmaker, "cliente@teste.com")


@pytest_asyncio.fixture
async def other(sessionmaker):
    return await add_user(sessionmaker, "outra@teste.com")


async def notify(maker, user, title, *, minutes=0, read=False, kind=NotificationType.APPOINTMENT_REMINDER):
    async with maker() as db:
        notification = Notification(
            user_id=user.id, title=title, message=f"Mensagem de {title}", type=kind, is_read=read,
            created_at=BASE + timedelta(minutes=minutes),
        )
        db.add(notification)
        await db.commit()
        return notification.id


async def titles(client, user):
    response = await client.get(URL, headers=auth(user))
    assert response.status_code == 200, response.text
    return [n["title"] for n in response.json()]


async def unread(client, user):
    response = await client.get(f"{URL}/unread-count", headers=auth(user))
    assert response.status_code == 200, response.text
    return response.json()["count"]


async def is_read(maker, notification_id):
    async with maker() as db:
        return (await db.get(Notification, notification_id)).is_read


# ── listar e contar ─────────────────────────────────────


async def test_list_shows_only_my_notifications_newest_first(client, member, other, sessionmaker):
    await notify(sessionmaker, member, "Primeira", minutes=0)
    await notify(sessionmaker, member, "Terceira", minutes=20, read=True, kind=NotificationType.LOYALTY_UPDATE)
    await notify(sessionmaker, member, "Segunda", minutes=10)
    await notify(sessionmaker, other, "Da outra", minutes=30)

    response = await client.get(URL, headers=auth(member))
    body = response.json()
    assert [n["title"] for n in body] == ["Terceira", "Segunda", "Primeira"]
    assert body[0]["message"] == "Mensagem de Terceira"
    assert (body[0]["type"], body[0]["is_read"]) == ("loyalty_update", True)
    assert all(n["user_id"] == str(member.id) and n["id"] and n["created_at"] for n in body)
    assert await titles(client, other) == ["Da outra"]


async def test_empty_list_and_zero_unread(client, member):
    assert await titles(client, member) == []
    assert await unread(client, member) == 0


async def test_unread_count_is_per_user(client, member, other, sessionmaker):
    await notify(sessionmaker, member, "A")
    await notify(sessionmaker, member, "B", minutes=1)
    await notify(sessionmaker, member, "C", minutes=2, read=True)
    await notify(sessionmaker, other, "D")
    assert await unread(client, member) == 2
    assert await unread(client, other) == 1


# ── marcar como lida ────────────────────────────────────


async def test_mark_one_as_read(client, member, sessionmaker):
    first = await notify(sessionmaker, member, "A")
    second = await notify(sessionmaker, member, "B", minutes=1)

    response = await client.put(f"{URL}/{first}/read", headers=auth(member))
    assert response.status_code == 200, response.text
    assert (response.json()["id"], response.json()["is_read"]) == (str(first), True)
    assert await is_read(sessionmaker, first) is True
    assert await is_read(sessionmaker, second) is False
    assert await unread(client, member) == 1

    again = await client.put(f"{URL}/{first}/read", headers=auth(member))
    assert again.status_code == 200
    assert again.json()["is_read"] is True


async def test_cannot_mark_someone_elses_or_unknown_notification(client, member, other, sessionmaker):
    theirs = await notify(sessionmaker, other, "Da outra")
    for notification_id in (theirs, uuid.uuid4()):
        response = await client.put(f"{URL}/{notification_id}/read", headers=auth(member))
        assert response.status_code == 404
        assert response.json()["detail"] == "Notificação não encontrada."
    assert await is_read(sessionmaker, theirs) is False


async def test_mark_all_as_read_touches_only_mine(client, member, other, sessionmaker):
    await notify(sessionmaker, member, "A")
    await notify(sessionmaker, member, "B", minutes=1)
    await notify(sessionmaker, member, "C", minutes=2, read=True)
    theirs = await notify(sessionmaker, other, "D")

    response = await client.put(f"{URL}/read-all", headers=auth(member))
    assert response.status_code == 200
    assert response.json() == {"detail": "2 notificações marcadas como lidas."}
    assert await unread(client, member) == 0
    assert await is_read(sessionmaker, theirs) is False
    assert await unread(client, other) == 1

    again = await client.put(f"{URL}/read-all", headers=auth(member))
    assert again.json() == {"detail": "0 notificações marcadas como lidas."}


# ── aviso geral (admin) ─────────────────────────────────


async def test_broadcast_reaches_every_user(client, member, other, sessionmaker):
    admin = await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)
    barber = await add_barber(sessionmaker, "barbeiro@teste.com")
    body = {"title": "Feriado", "message": "Fechados na sexta-feira."}

    response = await client.post(f"{URL}/broadcast", json=body, headers=auth(admin))
    assert response.status_code == 201, response.text
    assert response.json() == {"detail": "Mensagem enviada para 4 usuários."}

    async with sessionmaker() as db:
        sent = list((await db.execute(select(Notification))).scalars().all())
    assert sorted(str(n.user_id) for n in sent) == sorted(str(u) for u in (member.id, other.id, admin.id, barber.user_id))
    assert all(
        (n.title, n.message, n.type, n.is_read) == ("Feriado", "Fechados na sexta-feira.", NotificationType.SYSTEM_ALERT, False)
        for n in sent
    )
    assert await titles(client, member) == ["Feriado"]
    assert await unread(client, other) == 1


@pytest.mark.parametrize("body", [{"title": "x" * 151, "message": "m"}, {"message": "m"}, {"title": "t"}])
async def test_invalid_broadcast_gets_422(client, member, sessionmaker, body):
    admin = await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)
    response = await client.post(f"{URL}/broadcast", json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, Notification) == 0


# ── notificação para um usuário (serviço) ───────────────


async def test_create_notification_for_one_user(client, member, other, sessionmaker):
    async with sessionmaker() as db:
        created = await NotificationService(db).create_notification(NotificationCreateRequest(
            user_id=member.id, title="Seus pontos", message="Você ganhou 10 pontos.",
            type=NotificationType.LOYALTY_UPDATE,
        ))
    assert (created.user_id, created.type, created.is_read) == (member.id, NotificationType.LOYALTY_UPDATE, False)
    assert created.id and created.created_at
    assert await titles(client, member) == ["Seus pontos"]
    assert await unread(client, member) == 1
    assert await titles(client, other) == []


# ── permissões ──────────────────────────────────────────


async def test_every_route_needs_a_token(client, member, sessionmaker):
    notification_id = await notify(sessionmaker, member, "A")
    responses = [
        await client.get(URL),
        await client.get(f"{URL}/unread-count"),
        await client.put(f"{URL}/read-all"),
        await client.put(f"{URL}/{notification_id}/read"),
        await client.post(f"{URL}/broadcast", json={"title": "t", "message": "m"}),
    ]
    assert [r.status_code for r in responses] == [403] * 5
    assert await is_read(sessionmaker, notification_id) is False
    assert await count(sessionmaker, Notification) == 1


@pytest.mark.parametrize("role", [UserRole.CLIENT, UserRole.BARBER])
async def test_broadcast_is_admin_only(client, sessionmaker, role):
    user = await add_user(sessionmaker, "outro@teste.com", role)
    response = await client.post(f"{URL}/broadcast", json={"title": "t", "message": "m"}, headers=auth(user))
    assert response.status_code == 403
    assert await count(sessionmaker, Notification) == 0
