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


# ── resgate ─────────────────────────────────────────────


async def test_redeem_debits_the_balance_and_keeps_lifetime(client, admin, member, sessionmaker):
    reward = await create_reward(client, admin, "Pomada", 120)
    await give(client, admin, member, 200)

    response = await redeem(client, member, reward["id"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["reward_id"] == reward["id"]
    assert body["points_spent"] == 120
    assert body["reward"]["name"] == "Pomada"
    assert body["redeemed_at"]
    mine = await wallet(client, member)
    assert body["wallet_id"] == mine["id"]
    assert (mine["balance"], mine["lifetime_points"]) == (80, 200)
    assert await count(sessionmaker, RewardRedemption) == 1


async def test_spending_the_exact_balance_leaves_zero(client, admin, member):
    reward = await create_reward(client, admin, "Pomada", 120)
    await give(client, admin, member, 120)
    assert (await redeem(client, member, reward["id"])).status_code == 201
    assert (await wallet(client, member))["balance"] == 0


async def test_insufficient_balance_changes_nothing(client, admin, member, sessionmaker):
    reward = await create_reward(client, admin, "Corte grátis", 300)
    await give(client, admin, member, 299)
    response = await redeem(client, member, reward["id"])
    assert response.status_code == 400
    assert response.json()["detail"] == "Saldo insuficiente. Você possui 299 pts e o prêmio custa 300 pts."
    assert (await wallet(client, member))["balance"] == 299
    assert await count(sessionmaker, RewardRedemption) == 0


async def test_new_member_without_points_cannot_redeem(client, admin, member):
    reward = await create_reward(client, admin, "Pomada", 120)
    response = await redeem(client, member, reward["id"])
    assert response.status_code == 400
    assert response.json()["detail"] == "Saldo insuficiente. Você possui 0 pts e o prêmio custa 120 pts."


async def test_unknown_or_inactive_reward_gets_400(client, admin, member, sessionmaker):
    reward = await create_reward(client, admin, "Pomada", 10)
    await client.put(f"{URL}/rewards/{reward['id']}", json={"is_active": False}, headers=auth(admin))
    await give(client, admin, member, 100)
    for reward_id in (reward["id"], uuid.uuid4()):
        response = await redeem(client, member, reward_id)
        assert response.status_code == 400
        assert response.json()["detail"] == NO_REWARD
    assert (await wallet(client, member))["balance"] == 100
    assert await count(sessionmaker, RewardRedemption) == 0


async def test_redemption_keeps_the_cost_of_the_moment(client, admin, member):
    reward = await create_reward(client, admin, "Pomada", 120)
    await give(client, admin, member, 500)
    first = (await redeem(client, member, reward["id"])).json()
    await client.put(f"{URL}/rewards/{reward['id']}", json={"points_cost": 200}, headers=auth(admin))
    second = (await redeem(client, member, reward["id"])).json()
    assert (first["points_spent"], second["points_spent"]) == (120, 200)
    assert (await wallet(client, member))["balance"] == 180

    history = (await client.get(f"{URL}/redemptions", headers=auth(admin))).json()
    assert [r["points_spent"] for r in history] == [200, 120]


# ── resgates (admin) ────────────────────────────────────


async def test_admin_sees_every_redemption_newest_first(client, admin, member, sessionmaker):
    other = await add_user(sessionmaker, "outra@teste.com")
    pomade = await create_reward(client, admin, "Pomada", 50)
    cut = await create_reward(client, admin, "Corte grátis", 100)
    await give(client, admin, member, 100)
    await give(client, admin, other, 100)
    first = (await redeem(client, member, pomade["id"])).json()
    second = (await redeem(client, other, cut["id"])).json()

    response = await client.get(f"{URL}/redemptions", headers=auth(admin))
    assert response.status_code == 200
    body = response.json()
    assert [r["id"] for r in body] == [second["id"], first["id"]]
    assert [r["reward"]["name"] for r in body] == ["Corte grátis", "Pomada"]


async def test_no_redemptions(client, admin):
    response = await client.get(f"{URL}/redemptions", headers=auth(admin))
    assert response.status_code == 200
    assert response.json() == []


# ── permissões ──────────────────────────────────────────


async def test_wallet_and_redeem_need_a_token(client, admin, sessionmaker):
    reward = await create_reward(client, admin, "Pomada", 10)
    assert (await client.get(f"{URL}/me")).status_code == 403
    assert (await client.post(f"{URL}/redeem/{reward['id']}")).status_code == 403
    assert await count(sessionmaker, LoyaltyWallet) == 0
    assert await count(sessionmaker, RewardRedemption) == 0


@pytest.mark.parametrize("role", [None, UserRole.CLIENT, UserRole.BARBER])
async def test_admin_routes_are_forbidden_to_others(client, admin, member, sessionmaker, role):
    reward = await create_reward(client, admin, "Pomada", 120)
    headers = auth(await add_user(sessionmaker, "outro@teste.com", role)) if role else {}
    responses = [
        await client.post(f"{URL}/rewards", json={"name": "Novo", "points_cost": 1}, headers=headers),
        await client.put(f"{URL}/rewards/{reward['id']}", json={"points_cost": 1}, headers=headers),
        await client.post(f"{URL}/wallet/{member.id}/add", params={"points": 1000}, headers=headers),
        await client.get(f"{URL}/redemptions", headers=headers),
    ]
    assert [r.status_code for r in responses] == [403] * 4
    assert await catalog(client) == ["Pomada"]
    assert (await client.get(f"{URL}/rewards")).json()[0]["points_cost"] == 120
    assert await wallet_in_db(sessionmaker, member) is None


async def test_catalog_is_public(client, admin):
    await create_reward(client, admin, "Pomada", 120)
    assert await catalog(client) == ["Pomada"]
