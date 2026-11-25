"""
Testes de integração do programa de fidelidade: carteira, prêmios e resgates (#3).

Spec: SPEC/2026-11-24-testes-integracao-loyalty.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Substituem o tests/test_loyalty.py gerado, que não importava a aplicação.
Hoje os pontos só entram pelo admin (#13).
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.auth.models import UserRole
from src.backend.modules.loyalty.models import LoyaltyWallet, Reward, RewardRedemption
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/loyalty"
NO_REWARD = "Prêmio não encontrado ou inativo."
POSITIVE = "A quantidade de pontos deve ser maior que zero."


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


@pytest_asyncio.fixture
async def member(sessionmaker):
    return await add_user(sessionmaker, "cliente@teste.com")


async def create_reward(client, admin, name="Corte grátis", cost=100, **extra):
    response = await client.post(
        f"{URL}/rewards", json={"name": name, "points_cost": cost, **extra}, headers=auth(admin)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def give(client, admin, user, points):
    return await client.post(f"{URL}/wallet/{user.id}/add", params={"points": points}, headers=auth(admin))


async def wallet(client, user):
    response = await client.get(f"{URL}/me", headers=auth(user))
    assert response.status_code == 200, response.text
    return response.json()


async def redeem(client, user, reward_id):
    return await client.post(f"{URL}/redeem/{reward_id}", headers=auth(user))


async def wallet_in_db(maker, user):
    async with maker() as db:
        return (await db.execute(select(LoyaltyWallet).where(LoyaltyWallet.user_id == user.id))).scalar_one_or_none()


async def catalog(client):
    response = await client.get(f"{URL}/rewards")
    assert response.status_code == 200, response.text
    return [r["name"] for r in response.json()]


# ── carteira ────────────────────────────────────────────


async def test_first_access_creates_an_empty_wallet(client, member, sessionmaker):
    body = await wallet(client, member)
    assert body["user_id"] == str(member.id)
    assert (body["balance"], body["lifetime_points"]) == (0, 0)
    assert body["id"] and body["updated_at"]

    again = await wallet(client, member)
    assert again["id"] == body["id"]
    assert await count(sessionmaker, LoyaltyWallet) == 1


async def test_each_user_has_their_own_wallet(client, admin, member, sessionmaker):
    other = await add_user(sessionmaker, "outra@teste.com")
    await give(client, admin, member, 30)
    assert (await wallet(client, other))["balance"] == 0
    assert (await wallet(client, member))["balance"] == 30
    assert await count(sessionmaker, LoyaltyWallet) == 2


# ── pontos dados pelo admin ─────────────────────────────


async def test_admin_points_add_to_balance_and_lifetime(client, admin, member, sessionmaker):
    first = await give(client, admin, member, 40)
    assert first.status_code == 200, first.text
    assert (first.json()["balance"], first.json()["lifetime_points"]) == (40, 40)
    assert first.json()["user_id"] == str(member.id)

    second = (await give(client, admin, member, 25)).json()
    assert (second["balance"], second["lifetime_points"]) == (65, 65)
    saved = await wallet_in_db(sessionmaker, member)
    assert (saved.balance, saved.lifetime_points) == (65, 65)


@pytest.mark.parametrize("points", [0, -10])
async def test_zero_or_negative_points_get_400(client, admin, member, sessionmaker, points):
    await give(client, admin, member, 20)
    response = await give(client, admin, member, points)
    assert response.status_code == 400
    assert response.json()["detail"] == POSITIVE
    saved = await wallet_in_db(sessionmaker, member)
    assert (saved.balance, saved.lifetime_points) == (20, 20)


@pytest.mark.parametrize("params", [{}, {"points": "dez"}, {"points": 1.5}])
async def test_invalid_points_get_422(client, admin, member, params):
    response = await client.post(f"{URL}/wallet/{member.id}/add", params=params, headers=auth(admin))
    assert response.status_code == 422


# ── catálogo e prêmios ──────────────────────────────────


async def test_catalog_lists_active_rewards_cheapest_first(client, admin):
    await create_reward(client, admin, "Corte grátis", 300)
    await create_reward(client, admin, "Pomada", 120)
    hidden = await create_reward(client, admin, "Barba grátis", 50)
    await client.put(f"{URL}/rewards/{hidden['id']}", json={"is_active": False}, headers=auth(admin))
    assert await catalog(client) == ["Pomada", "Corte grátis"]


async def test_empty_catalog(client, sessionmaker):
    assert await catalog(client) == []


async def test_create_reward(client, admin, sessionmaker):
    body = await create_reward(client, admin, "Corte grátis", 300, description="Um corte simples")
    assert (body["name"], body["description"], body["points_cost"], body["is_active"]) == (
        "Corte grátis", "Um corte simples", 300, True,
    )
    assert body["created_at"]
    async with sessionmaker() as db:
        saved = await db.get(Reward, uuid.UUID(body["id"]))
    assert (saved.name, saved.points_cost, saved.is_active) == ("Corte grátis", 300, True)


async def test_update_reward_changes_only_sent_fields(client, admin):
    reward = await create_reward(client, admin, "Corte grátis", 300, description="Simples")
    response = await client.put(f"{URL}/rewards/{reward['id']}", json={"points_cost": 250}, headers=auth(admin))
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["name"], body["description"], body["points_cost"], body["is_active"]) == (
        "Corte grátis", "Simples", 250, True,
    )


async def test_deactivate_and_reactivate_a_reward(client, admin):
    reward = await create_reward(client, admin, "Pomada", 120)
    off = await client.put(f"{URL}/rewards/{reward['id']}", json={"is_active": False}, headers=auth(admin))
    assert off.json()["is_active"] is False
    assert await catalog(client) == []
    on = await client.put(f"{URL}/rewards/{reward['id']}", json={"is_active": True}, headers=auth(admin))
    assert on.json()["is_active"] is True
    assert await catalog(client) == ["Pomada"]


async def test_update_unknown_reward_gets_404(client, admin):
    response = await client.put(f"{URL}/rewards/{uuid.uuid4()}", json={"points_cost": 10}, headers=auth(admin))
    assert response.status_code == 404
    assert response.json()["detail"] == "Prêmio não encontrado."


@pytest.mark.parametrize(
    "body",
    [{"name": "P", "points_cost": 0}, {"name": "P", "points_cost": -5}, {"name": "x" * 151, "points_cost": 10},
     {"name": "P", "points_cost": 10, "description": "x" * 501}, {"points_cost": 10}, {"name": "P"}],
)
async def test_invalid_reward_gets_422(client, admin, sessionmaker, body):
    response = await client.post(f"{URL}/rewards", json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, Reward) == 0


@pytest.mark.parametrize("body", [{"points_cost": 0}, {"name": "x" * 151}, {"description": "x" * 501}])
async def test_invalid_update_gets_422(client, admin, body):
    reward = await create_reward(client, admin, "Pomada", 120)
    response = await client.put(f"{URL}/rewards/{reward['id']}", json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await catalog(client) == ["Pomada"]
