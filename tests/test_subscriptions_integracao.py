"""
Testes de integração do Trim Club: planos e assinaturas (#3).

Spec: SPEC/2026-11-24-testes-integracao-subscriptions.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Substituem o tests/test_subscriptions.py gerado, que não importava a
aplicação.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.auth.models import UserRole
from src.backend.modules.subscriptions.models import SubscriptionPlan, SubscriptionStatus, UserSubscription
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/subscriptions"
DUPLICATE = "Já existe um plano com esse nome."
UNAVAILABLE = "Plano inválido ou indisponível."
ALREADY = "O usuário já possui uma assinatura ativa ou em período de carência. Cancele-a ou aguarde expirar."
PLAN_FIELDS = {
    "id", "name", "description", "monthly_price", "included_cuts", "included_shaves",
    "discount_percentage", "is_active", "created_at",
}


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


@pytest_asyncio.fixture
async def member(sessionmaker):
    return await add_user(sessionmaker, "socio@teste.com")


async def create_plan(client, admin, name="Básico", price="59.90", **extra):
    response = await client.post(
        f"{URL}/plans", json={"name": name, "monthly_price": price, **extra}, headers=auth(admin)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def subscribe(client, user, plan_id):
    return await client.post(f"{URL}/me/subscribe/{plan_id}", headers=auth(user))


async def plan_in_db(maker, plan_id):
    async with maker() as db:
        return await db.get(SubscriptionPlan, uuid.UUID(str(plan_id)))


async def subscriptions_in_db(maker):
    async with maker() as db:
        return list((await db.execute(select(UserSubscription))).scalars().all())


async def public_names(client):
    response = await client.get(f"{URL}/plans")
    assert response.status_code == 200, response.text
    return [p["name"] for p in response.json()]


# ── planos públicos ─────────────────────────────────────


async def test_public_plans_are_active_ones_cheapest_first(client, admin):
    await create_plan(client, admin, "Executivo", "149.90")
    await create_plan(client, admin, "Básico", "59.90")
    gone = await create_plan(client, admin, "Antigo", "10.00")
    await client.delete(f"{URL}/plans/{gone['id']}", headers=auth(admin))
    await create_plan(client, admin, "Plus", "99.00")

    assert await public_names(client) == ["Básico", "Plus", "Executivo"]


async def test_public_plan_shows_its_benefits(client, admin):
    await create_plan(
        client, admin, "Plus", "99.00", description="Corte e barba", included_cuts=4, included_shaves=2,
        discount_percentage="10",
    )
    [plan] = (await client.get(f"{URL}/plans")).json()
    assert set(plan) == PLAN_FIELDS
    assert (plan["name"], plan["description"], plan["included_cuts"], plan["included_shaves"]) == (
        "Plus", "Corte e barba", 4, 2,
    )
    assert Decimal(plan["monthly_price"]) == Decimal("99.00")
    assert Decimal(plan["discount_percentage"]) == Decimal("10.00")
    assert plan["is_active"] is True


async def test_no_plans(client, sessionmaker):
    response = await client.get(f"{URL}/plans")
    assert response.status_code == 200
    assert response.json() == []


# ── criação de plano ────────────────────────────────────


async def test_create_plan_with_defaults(client, admin, sessionmaker):
    plan = await create_plan(client, admin, "Básico", "59.9")
    assert plan["is_active"] is True
    assert Decimal(plan["monthly_price"]) == Decimal("59.90")
    assert (plan["included_cuts"], plan["included_shaves"]) == (0, 0)
    assert Decimal(plan["discount_percentage"]) == Decimal("0.00")
    assert plan["description"] is None
    saved = await plan_in_db(sessionmaker, plan["id"])
    assert (saved.name, Decimal(saved.monthly_price), saved.is_active) == ("Básico", Decimal("59.90"), True)


async def test_create_plan_limits_are_accepted(client, admin):
    plan = await create_plan(client, admin, "x" * 100, "0.01", discount_percentage="100")
    assert len(plan["name"]) == 100
    assert Decimal(plan["discount_percentage"]) == Decimal("100.00")


@pytest.mark.parametrize("deactivated", [False, True])
async def test_duplicate_plan_name_gets_400(client, admin, sessionmaker, deactivated):
    plan = await create_plan(client, admin, "Básico")
    if deactivated:
        await client.delete(f"{URL}/plans/{plan['id']}", headers=auth(admin))
    response = await client.post(f"{URL}/plans", json={"name": "Básico", "monthly_price": 1}, headers=auth(admin))
    assert response.status_code == 400
    assert response.json()["detail"] == DUPLICATE
    assert await count(sessionmaker, SubscriptionPlan) == 1


@pytest.mark.parametrize(
    "body",
    [
        {"name": "P", "monthly_price": 0},
        {"name": "P", "monthly_price": -10},
        {"name": "P", "monthly_price": 10, "included_cuts": -1},
        {"name": "P", "monthly_price": 10, "included_shaves": -1},
        {"name": "P", "monthly_price": 10, "discount_percentage": -1},
        {"name": "P", "monthly_price": 10, "discount_percentage": "100.01"},
        {"name": "x" * 101, "monthly_price": 10},
        {"monthly_price": 10},
        {"name": "P"},
    ],
)
async def test_invalid_plan_gets_422(client, admin, sessionmaker, body):
    response = await client.post(f"{URL}/plans", json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, SubscriptionPlan) == 0


# ── alteração e desativação de plano ────────────────────


async def test_update_plan_changes_only_sent_fields(client, admin, sessionmaker):
    plan = await create_plan(client, admin, "Plus", "99.00", included_cuts=4, description="Corte")
    response = await client.put(
        f"{URL}/plans/{plan['id']}", json={"monthly_price": "109.90", "included_shaves": 2}, headers=auth(admin)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(body["monthly_price"]) == Decimal("109.90")
    assert (body["name"], body["description"], body["included_cuts"], body["included_shaves"]) == (
        "Plus", "Corte", 4, 2,
    )
    saved = await plan_in_db(sessionmaker, plan["id"])
    assert (Decimal(saved.monthly_price), saved.included_shaves, saved.included_cuts) == (Decimal("109.90"), 2, 4)


async def test_update_plan_every_field(client, admin):
    plan = await create_plan(client, admin, "Plus")
    changes = {"name": "Plus+", "description": "Novo", "monthly_price": "120", "included_cuts": 5,
               "included_shaves": 3, "discount_percentage": "15.5"}
    body = (await client.put(f"{URL}/plans/{plan['id']}", json=changes, headers=auth(admin))).json()
    assert (body["name"], body["description"], body["included_cuts"], body["included_shaves"]) == (
        "Plus+", "Novo", 5, 3,
    )
    assert (Decimal(body["monthly_price"]), Decimal(body["discount_percentage"])) == (
        Decimal("120.00"), Decimal("15.50"),
    )


async def test_update_to_another_plans_name_gets_400(client, admin, sessionmaker):
    await create_plan(client, admin, "Básico")
    other = await create_plan(client, admin, "Plus")
    response = await client.put(f"{URL}/plans/{other['id']}", json={"name": "Básico"}, headers=auth(admin))
    assert response.status_code == 400
    assert response.json()["detail"] == DUPLICATE
    assert (await plan_in_db(sessionmaker, other["id"])).name == "Plus"


async def test_update_keeping_own_name_is_accepted(client, admin):
    plan = await create_plan(client, admin, "Plus")
    response = await client.put(
        f"{URL}/plans/{plan['id']}", json={"name": "Plus", "included_cuts": 2}, headers=auth(admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["included_cuts"] == 2


async def test_update_unknown_plan_gets_404(client, admin):
    response = await client.put(f"{URL}/plans/{uuid.uuid4()}", json={"included_cuts": 1}, headers=auth(admin))
    assert response.status_code == 404
    assert response.json()["detail"] == "Plano não encontrado."


@pytest.mark.parametrize(
    "body",
    [{"monthly_price": 0}, {"included_cuts": -1}, {"discount_percentage": 101}, {"name": "x" * 101}],
)
async def test_invalid_update_gets_422(client, admin, sessionmaker, body):
    plan = await create_plan(client, admin, "Plus", "99.00")
    response = await client.put(f"{URL}/plans/{plan['id']}", json=body, headers=auth(admin))
    assert response.status_code == 422
    saved = await plan_in_db(sessionmaker, plan["id"])
    assert (saved.name, Decimal(saved.monthly_price), saved.included_cuts) == ("Plus", Decimal("99.00"), 0)


async def test_deactivate_plan_hides_it_but_keeps_members(client, admin, member, sessionmaker):
    plan = await create_plan(client, admin, "Plus")
    assert (await subscribe(client, member, plan["id"])).status_code == 201

    response = await client.delete(f"{URL}/plans/{plan['id']}", headers=auth(admin))
    assert response.status_code == 204
    assert await public_names(client) == []
    assert (await plan_in_db(sessionmaker, plan["id"])).is_active is False

    mine = (await client.get(f"{URL}/me", headers=auth(member))).json()
    assert mine["status"] == "active"
    assert mine["plan"]["id"] == plan["id"]
    assert mine["plan"]["is_active"] is False


async def test_deactivate_unknown_plan_gets_404(client, admin):
    response = await client.delete(f"{URL}/plans/{uuid.uuid4()}", headers=auth(admin))
    assert response.status_code == 404
    assert response.json()["detail"] == "Plano não encontrado."


# ── assinar, consultar e cancelar ───────────────────────


async def test_subscribe_starts_a_30_day_cycle(client, admin, member, sessionmaker):
    plan = await create_plan(client, admin, "Plus", "99.00", included_cuts=4)
    # O dia do servidor ou o da barbearia: o PR #88 (#64) passa a usar o fuso da barbearia.
    days = {date.today(), datetime.now(ZoneInfo("America/Sao_Paulo")).date()}
    response = await subscribe(client, member, plan["id"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_id"] == str(member.id)
    assert body["plan_id"] == plan["id"]
    assert body["status"] == "active"
    start = date.fromisoformat(body["start_date"])
    assert start in days
    assert date.fromisoformat(body["end_date"]) == start + timedelta(days=30)
    assert body["plan"]["name"] == "Plus"
    assert body["plan"]["included_cuts"] == 4
    assert body["created_at"] and body["updated_at"]

    [saved] = await subscriptions_in_db(sessionmaker)
    assert (saved.user_id, str(saved.plan_id), saved.status) == (member.id, plan["id"], SubscriptionStatus.ACTIVE)
    assert saved.end_date - saved.start_date == timedelta(days=30)


async def test_subscribe_to_unknown_or_inactive_plan_gets_400(client, admin, member, sessionmaker):
    plan = await create_plan(client, admin, "Antigo")
    await client.delete(f"{URL}/plans/{plan['id']}", headers=auth(admin))
    for plan_id in (plan["id"], uuid.uuid4()):
        response = await subscribe(client, member, plan_id)
        assert response.status_code == 400
        assert response.json()["detail"] == UNAVAILABLE
    assert await count(sessionmaker, UserSubscription) == 0


@pytest.mark.parametrize("cancel_first", [False, True])
async def test_member_cannot_subscribe_twice(client, admin, member, sessionmaker, cancel_first):
    plan = await create_plan(client, admin, "Básico")
    other = await create_plan(client, admin, "Plus", "99.00")
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    if cancel_first:
        assert (await client.put(f"{URL}/me/cancel", headers=auth(member))).status_code == 200

    response = await subscribe(client, member, other["id"])
    assert response.status_code == 400
    assert response.json()["detail"] == ALREADY
    [saved] = await subscriptions_in_db(sessionmaker)
    assert str(saved.plan_id) == plan["id"]


async def test_each_member_has_their_own_subscription(client, admin, member, sessionmaker):
    other = await add_user(sessionmaker, "outro@teste.com")
    basic = await create_plan(client, admin, "Básico")
    plus = await create_plan(client, admin, "Plus", "99.00")
    await subscribe(client, member, basic["id"])
    await subscribe(client, other, plus["id"])

    mine = (await client.get(f"{URL}/me", headers=auth(member))).json()
    theirs = (await client.get(f"{URL}/me", headers=auth(other))).json()
    assert (mine["user_id"], mine["plan"]["name"]) == (str(member.id), "Básico")
    assert (theirs["user_id"], theirs["plan"]["name"]) == (str(other.id), "Plus")


async def test_without_subscription_me_gets_404(client, member):
    response = await client.get(f"{URL}/me", headers=auth(member))
    assert response.status_code == 404
    assert response.json()["detail"] == "Você não possui uma assinatura."


async def test_cancel_keeps_dates_and_marks_canceled(client, admin, member, sessionmaker):
    plan = await create_plan(client, admin, "Plus")
    subscribed = (await subscribe(client, member, plan["id"])).json()

    response = await client.put(f"{URL}/me/cancel", headers=auth(member))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "canceled"
    assert (body["start_date"], body["end_date"]) == (subscribed["start_date"], subscribed["end_date"])
    assert body["plan"]["id"] == plan["id"]

    [saved] = await subscriptions_in_db(sessionmaker)
    assert saved.status == SubscriptionStatus.CANCELED
    assert (await client.get(f"{URL}/me", headers=auth(member))).json()["status"] == "canceled"


async def test_cancel_twice_gets_400(client, admin, member):
    plan = await create_plan(client, admin, "Plus")
    await subscribe(client, member, plan["id"])
    await client.put(f"{URL}/me/cancel", headers=auth(member))
    response = await client.put(f"{URL}/me/cancel", headers=auth(member))
    assert response.status_code == 400
    assert response.json()["detail"] == "Esta assinatura já está cancelada."


async def test_cancel_without_subscription_gets_404(client, member):
    response = await client.put(f"{URL}/me/cancel", headers=auth(member))
    assert response.status_code == 404
    assert response.json()["detail"] == "Assinatura não encontrada."


async def test_cancel_touches_only_my_subscription(client, admin, member, sessionmaker):
    other = await add_user(sessionmaker, "outro@teste.com")
    plan = await create_plan(client, admin, "Plus")
    await subscribe(client, member, plan["id"])
    await subscribe(client, other, plan["id"])
    await client.put(f"{URL}/me/cancel", headers=auth(member))
    assert (await client.get(f"{URL}/me", headers=auth(other))).json()["status"] == "active"


# ── lista do admin ──────────────────────────────────────


async def test_admin_lists_every_subscription_newest_first(client, admin, member, sessionmaker):
    other = await add_user(sessionmaker, "outro@teste.com")
    basic = await create_plan(client, admin, "Básico")
    plus = await create_plan(client, admin, "Plus", "99.00")
    first = (await subscribe(client, member, basic["id"])).json()
    await client.put(f"{URL}/me/cancel", headers=auth(member))
    second = (await subscribe(client, other, plus["id"])).json()

    response = await client.get(f"{URL}/users", headers=auth(admin))
    assert response.status_code == 200
    body = response.json()
    assert [s["id"] for s in body] == [second["id"], first["id"]]
    assert [(s["status"], s["plan"]["name"]) for s in body] == [("active", "Plus"), ("canceled", "Básico")]


async def test_admin_list_is_empty_without_members(client, admin):
    response = await client.get(f"{URL}/users", headers=auth(admin))
    assert response.status_code == 200
    assert response.json() == []


# ── permissões ──────────────────────────────────────────


@pytest.mark.parametrize("role", [None, UserRole.CLIENT, UserRole.BARBER])
async def test_admin_routes_are_forbidden_to_others(client, admin, sessionmaker, role):
    plan = await create_plan(client, admin, "Plus", "99.00")
    headers = auth(await add_user(sessionmaker, "outro@teste.com", role)) if role else {}
    requests = [
        ("post", f"{URL}/plans", {"name": "Novo", "monthly_price": 10}),
        ("put", f"{URL}/plans/{plan['id']}", {"monthly_price": 1}),
        ("delete", f"{URL}/plans/{plan['id']}", None),
        ("get", f"{URL}/users", None),
    ]
    for method, url, body in requests:
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        response = await getattr(client, method)(url, **kwargs)
        assert response.status_code == 403, (method, url, response.text)

    saved = await plan_in_db(sessionmaker, plan["id"])
    assert (saved.is_active, Decimal(saved.monthly_price)) == (True, Decimal("99.00"))
    assert await count(sessionmaker, SubscriptionPlan) == 1


async def test_member_routes_need_a_token(client, admin, sessionmaker):
    plan = await create_plan(client, admin, "Plus")
    for method, url in [("get", f"{URL}/me"), ("post", f"{URL}/me/subscribe/{plan['id']}"), ("put", f"{URL}/me/cancel")]:
        response = await getattr(client, method)(url)
        assert response.status_code == 403, (method, url)
    assert await count(sessionmaker, UserSubscription) == 0


async def test_plan_list_is_public(client, admin):
    await create_plan(client, admin, "Plus")
    assert await public_names(client) == ["Plus"]
