"""
Fidelidade: usuário desconhecido, null no PUT, nomes de prêmio, trava no resgate e operações do
admin (#73).

Spec: SPEC/2026-11-25-fidelidade-correcoes.md
"""

import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from src.backend.modules.auth.models import UserRole
from src.backend.modules.loyalty.models import LoyaltyWallet, Reward, RewardRedemption
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/loyalty"


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


@pytest_asyncio.fixture
async def member(sessionmaker):
    return await add_user(sessionmaker, "cliente@teste.com", full_name="Ana Lima")


async def create_reward(client, admin, name="Pomada", cost=100):
    response = await client.post(f"{URL}/rewards", json={"name": name, "points_cost": cost}, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


async def points(client, admin, user_id, amount, action="add"):
    return await client.post(f"{URL}/wallet/{user_id}/{action}", params={"points": amount, "reason": "Correção"}, headers=auth(admin))


async def balance(client, user):
    return (await client.get(f"{URL}/me", headers=auth(user))).json()


# ── 1. usuário desconhecido ─────────────────────────────


@pytest.mark.parametrize("action", ["add", "remove"])
async def test_points_for_unknown_user_get_404(client, sessionmaker, admin, action):
    response = await points(client, admin, uuid.uuid4(), 10, action)
    assert response.status_code == 404
    assert response.json()["detail"] == "Usuário não encontrado."
    assert await count(sessionmaker, LoyaltyWallet) == 0


# ── 2. PUT de prêmio com null ───────────────────────────


@pytest.mark.parametrize("field", ["name", "points_cost", "is_active"])
async def test_put_reward_with_null_gets_422(client, sessionmaker, admin, field):
    reward = await create_reward(client, admin)
    response = await client.put(f"{URL}/rewards/{reward['id']}", json={field: None}, headers=auth(admin))
    assert response.status_code == 422
    async with sessionmaker() as db:
        saved = await db.get(Reward, uuid.UUID(reward["id"]))
    assert (saved.name, saved.points_cost, saved.is_active) == ("Pomada", 100, True)


async def test_put_reward_can_clear_the_description(client, admin):
    reward = await create_reward(client, admin)
    response = await client.put(f"{URL}/rewards/{reward['id']}", json={"description": None}, headers=auth(admin))
    assert response.status_code == 200
    assert response.json()["description"] is None


# ── 3. nomes de prêmio ──────────────────────────────────


@pytest.mark.parametrize("name", ["", "   "])
async def test_blank_reward_name_gets_422(client, sessionmaker, admin, name):
    response = await client.post(f"{URL}/rewards", json={"name": name, "points_cost": 10}, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, Reward) == 0


async def test_reward_name_is_trimmed(client, admin):
    assert (await create_reward(client, admin, "  Pomada  "))["name"] == "Pomada"


@pytest.mark.parametrize("name", ["Pomada", "pomada", " POMADA "])
async def test_duplicate_reward_name_gets_400(client, sessionmaker, admin, name):
    await create_reward(client, admin, "Pomada")
    response = await client.post(f"{URL}/rewards", json={"name": name, "points_cost": 10}, headers=auth(admin))
    assert response.status_code == 400
    assert response.json()["detail"] == f"Já existe um prêmio chamado '{name.strip()}'."
    assert await count(sessionmaker, Reward) == 1


async def test_rename_to_another_rewards_name_gets_400(client, admin):
    await create_reward(client, admin, "Pomada")
    cut = await create_reward(client, admin, "Corte")
    response = await client.put(f"{URL}/rewards/{cut['id']}", json={"name": "pomada"}, headers=auth(admin))
    assert response.status_code == 400


async def test_keeping_its_own_name_is_fine(client, admin):
    reward = await create_reward(client, admin, "Pomada")
    response = await client.put(f"{URL}/rewards/{reward['id']}", json={"name": "POMADA"}, headers=auth(admin))
    assert response.status_code == 200
    assert response.json()["name"] == "POMADA"


# ── 4. resgate travado ──────────────────────────────────


async def test_simultaneous_redemptions_cannot_overdraw(client, sessionmaker, admin, member):
    reward = await create_reward(client, admin, cost=100)
    assert (await points(client, admin, member.id, 100)).status_code == 200

    async def redeem():
        return await client.post(f"{URL}/redeem/{reward['id']}", headers=auth(member))

    responses = await asyncio.gather(*(redeem() for _ in range(4)))

    assert sorted(r.status_code for r in responses) == [201, 400, 400, 400]
    assert (await balance(client, member))["balance"] == 0
    assert await count(sessionmaker, RewardRedemption) == 1


async def test_database_refuses_negative_balance(sessionmaker, member):
    async with sessionmaker() as db:
        db.add(LoyaltyWallet(user_id=member.id, balance=0, lifetime_points=0))
        await db.commit()
    async with sessionmaker() as db:
        with pytest.raises(IntegrityError):
            await db.execute(update(LoyaltyWallet).values(balance=-1))
            await db.commit()


# ── 5. operações do admin ───────────────────────────────


async def test_admin_removes_points_without_touching_lifetime(client, admin, member):
    await points(client, admin, member.id, 100)
    response = await points(client, admin, member.id, 30, "remove")
    assert response.status_code == 200, response.text
    assert (response.json()["balance"], response.json()["lifetime_points"]) == (70, 100)


async def test_removing_more_than_the_balance_gets_400(client, admin, member):
    await points(client, admin, member.id, 20)
    response = await points(client, admin, member.id, 21, "remove")
    assert response.status_code == 400
    assert response.json()["detail"] == "Saldo insuficiente para retirar 21 pts. O cliente possui 20 pts."
    assert (await balance(client, member))["balance"] == 20


@pytest.mark.parametrize("amount", [0, -5])
async def test_removing_zero_or_negative_gets_400(client, admin, member, amount):
    assert (await points(client, admin, member.id, amount, "remove")).status_code == 400


async def test_admin_lists_wallets_with_the_client(client, sessionmaker, admin, member):
    other = await add_user(sessionmaker, "bia@teste.com", full_name="Bia Souza")
    await points(client, admin, member.id, 10)
    await points(client, admin, other.id, 50)

    response = await client.get(f"{URL}/wallets", headers=auth(admin))

    assert response.status_code == 200
    body = response.json()
    assert [(w["full_name"], w["email"], w["balance"]) for w in body] == [
        ("Bia Souza", "bia@teste.com", 50),
        ("Ana Lima", "cliente@teste.com", 10),
    ]


async def test_redemptions_show_the_client(client, admin, member):
    reward = await create_reward(client, admin, cost=10)
    await points(client, admin, member.id, 10)
    redeemed = (await client.post(f"{URL}/redeem/{reward['id']}", headers=auth(member))).json()
    assert redeemed["user_id"] == str(member.id)

    listed = (await client.get(f"{URL}/redemptions", headers=auth(admin))).json()
    assert [r["user_id"] for r in listed] == [str(member.id)]


@pytest.mark.parametrize("route", ["wallets", "remove"])
async def test_new_admin_routes_are_admin_only(client, sessionmaker, member, route):
    if route == "wallets":
        response = await client.get(f"{URL}/wallets", headers=auth(member))
    else:
        response = await points(client, member, member.id, 1, "remove")
    assert response.status_code == 403
