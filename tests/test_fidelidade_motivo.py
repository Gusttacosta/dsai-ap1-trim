"""
Fidelidade: o motivo obrigatório do ajuste manual de pontos, que vai na notificação (#110).

Spec: SPEC/2026-11-26-painel-fidelidade.md

As regras do motivo rodam sem banco; as rotas usam o PostgreSQL de TEST_DATABASE_URL.
"""

import pytest
import pytest_asyncio
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select

from src.backend.modules.auth.models import UserRole
from src.backend.modules.loyalty.models import LoyaltyWallet
from src.backend.modules.loyalty.schemas import AdjustmentReason
from src.backend.modules.notifications.models import Notification, NotificationType
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_user, auth

URL = "/api/loyalty"
REASON = TypeAdapter(AdjustmentReason)


# ── a regra do motivo, sem banco ────────────────────────


def test_reason_is_trimmed():
    assert REASON.validate_python("  Aniversário  ") == "Aniversário"


@pytest.mark.parametrize("reason", ["", "ab", "  ab  ", "x" * 201])
def test_reason_outside_3_to_200_is_refused(reason):
    with pytest.raises(ValidationError):
        REASON.validate_python(reason)


def test_reason_of_200_is_accepted():
    assert REASON.validate_python("x" * 200) == "x" * 200


# ── as rotas, com banco ─────────────────────────────────


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


@pytest_asyncio.fixture
async def member(sessionmaker):
    return await add_user(sessionmaker, "cliente@teste.com", full_name="Ana Lima")


async def adjust(client, admin, user, action, points, **reason):
    params = {"points": points, **reason}
    return await client.post(f"{URL}/wallet/{user.id}/{action}", params=params, headers=auth(admin))


async def notices(maker, user):
    async with maker() as db:
        rows = await db.execute(
            select(Notification.title, Notification.message)
            .where(Notification.user_id == user.id, Notification.type == NotificationType.LOYALTY_UPDATE)
            .order_by(Notification.created_at)
        )
        return [tuple(r) for r in rows.all()]


async def balance_in_db(maker, user):
    async with maker() as db:
        wallet = (await db.execute(select(LoyaltyWallet).where(LoyaltyWallet.user_id == user.id))).scalar_one_or_none()
        return None if wallet is None else (wallet.balance, wallet.lifetime_points)


@pytest.mark.asyncio
@needs_db
@pytest.mark.parametrize("action", ["add", "remove"])
@pytest.mark.parametrize("reason", [{}, {"reason": "  ab "}, {"reason": "x" * 201}])
async def test_adjust_without_a_valid_reason_gets_422(client, sessionmaker, admin, member, action, reason):
    response = await adjust(client, admin, member, action, 10, **reason)
    assert response.status_code == 422
    assert any(error["loc"] == ["query", "reason"] for error in response.json()["detail"])
    assert await count(sessionmaker, LoyaltyWallet) == 0
    assert await notices(sessionmaker, member) == []


@pytest.mark.asyncio
@needs_db
async def test_add_tells_the_client_the_reason(client, sessionmaker, admin, member):
    response = await adjust(client, admin, member, "add", 50, reason="  Aniversário  ")
    assert response.status_code == 200, response.text
    assert response.json()["balance"] == 50
    assert await notices(sessionmaker, member) == [
        ("Você ganhou pontos", "+50 pts da barbearia: Aniversário. Saldo: 50 pts."),
    ]


@pytest.mark.asyncio
@needs_db
async def test_remove_notifies_with_the_reason(client, sessionmaker, admin, member):
    await adjust(client, admin, member, "add", 120, reason="Cortesia")
    response = await adjust(client, admin, member, "remove", 50, reason="Lançamento em dobro")
    assert response.status_code == 200, response.text
    assert await balance_in_db(sessionmaker, member) == (70, 120)
    assert (await notices(sessionmaker, member))[-1] == (
        "Pontos retirados", "-50 pts: Lançamento em dobro. Saldo: 70 pts.",
    )


@pytest.mark.asyncio
@needs_db
async def test_refused_remove_does_not_notify(client, sessionmaker, admin, member):
    await adjust(client, admin, member, "add", 30, reason="Cortesia")
    response = await adjust(client, admin, member, "remove", 50, reason="Correção")
    assert response.status_code == 400
    assert response.json()["detail"] == "Saldo insuficiente para retirar 50 pts. O cliente possui 30 pts."
    assert await balance_in_db(sessionmaker, member) == (30, 30)
    assert [title for title, _ in await notices(sessionmaker, member)] == ["Você ganhou pontos"]
