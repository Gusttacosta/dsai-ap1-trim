"""
Trim Club: renovação depois do fim, vencimento, mensalidade no caixa, só clientes, dia da barbearia,
avisos e planos validados (#64).

Spec: SPEC/2026-11-25-trim-club-ciclo.md
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from src.backend.modules.auth.models import UserRole
from src.backend.modules.finance.models import PaymentMethod, Transaction, TransactionType
from src.backend.modules.notifications.models import Notification, NotificationType
from src.backend.modules.subscriptions import service as subscription_service
from src.backend.modules.subscriptions.models import SubscriptionPlan, SubscriptionStatus, UserSubscription
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/subscriptions"
BRT = ZoneInfo("America/Sao_Paulo")
ALREADY = "O usuário já possui uma assinatura ativa ou em período de carência. Cancele-a ou aguarde expirar."


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


@pytest_asyncio.fixture
async def member(sessionmaker):
    return await add_user(sessionmaker, "cliente@teste.com")


@pytest_asyncio.fixture
async def plan(client, admin):
    body = {"name": "Clássico", "monthly_price": "89.90", "included_cuts": 2}
    response = await client.post(f"{URL}/plans", json=body, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


def shop_today():
    return datetime.now(BRT).date()


async def subscribe(client, user, plan_id, body=None):
    kwargs = {"json": body} if body is not None else {}
    return await client.post(f"{URL}/me/subscribe/{plan_id}", headers=auth(user), **kwargs)


async def move_dates(maker, user_id, *, start, end, status=None):
    values = {"start_date": start, "end_date": end}
    if status is not None:
        values["status"] = status
    async with maker() as db:
        await db.execute(update(UserSubscription).where(UserSubscription.user_id == user_id).values(**values))
        await db.commit()


# ── 1. assinar de novo ──────────────────────────────────


@pytest.mark.parametrize("status", [SubscriptionStatus.CANCELED, SubscriptionStatus.ACTIVE])
async def test_member_subscribes_again_after_the_end(client, sessionmaker, member, plan, status):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    old_end = shop_today() - timedelta(days=1)
    await move_dates(sessionmaker, member.id, start=old_end - timedelta(days=30), end=old_end, status=status)

    response = await subscribe(client, member, plan["id"])

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "active"
    assert date.fromisoformat(body["start_date"]) == shop_today()
    assert date.fromisoformat(body["end_date"]) == shop_today() + timedelta(days=30)
    assert await count(sessionmaker, UserSubscription) == 1  # o mesmo registro, renovado


async def test_renewal_can_change_the_plan(client, sessionmaker, admin, member, plan):
    other = (await client.post(f"{URL}/plans", json={"name": "Executivo", "monthly_price": "149.90"},
                               headers=auth(admin))).json()
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    await client.put(f"{URL}/me/cancel", headers=auth(member))
    yesterday = shop_today() - timedelta(days=1)
    await move_dates(sessionmaker, member.id, start=yesterday - timedelta(days=30), end=yesterday)

    response = await subscribe(client, member, other["id"])

    assert response.status_code == 201
    assert response.json()["plan"]["name"] == "Executivo"


async def test_canceled_still_in_paid_period_cannot_subscribe_again(client, member, plan):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    await client.put(f"{URL}/me/cancel", headers=auth(member))
    response = await subscribe(client, member, plan["id"])
    assert response.status_code == 400
    assert response.json()["detail"] == ALREADY


async def test_last_day_still_counts_as_active(client, sessionmaker, member, plan):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    await move_dates(sessionmaker, member.id, start=shop_today() - timedelta(days=30), end=shop_today())
    assert (await subscribe(client, member, plan["id"])).status_code == 400
    assert (await client.get(f"{URL}/me", headers=auth(member))).json()["status"] == "active"


# ── 2. vencimento ───────────────────────────────────────


async def test_active_subscription_becomes_past_due_after_the_end(client, sessionmaker, admin, member, plan):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    yesterday = shop_today() - timedelta(days=1)
    await move_dates(sessionmaker, member.id, start=yesterday - timedelta(days=30), end=yesterday)

    assert (await client.get(f"{URL}/me", headers=auth(member))).json()["status"] == "past_due"
    listed = (await client.get(f"{URL}/users", headers=auth(admin))).json()
    assert [s["status"] for s in listed] == ["past_due"]
    async with sessionmaker() as db:
        saved = (await db.execute(select(UserSubscription))).scalar_one()
    assert saved.status == SubscriptionStatus.PAST_DUE


async def test_admin_list_also_applies_the_due_date(client, sessionmaker, admin, member, plan):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    yesterday = shop_today() - timedelta(days=1)
    await move_dates(sessionmaker, member.id, start=yesterday - timedelta(days=30), end=yesterday)
    listed = (await client.get(f"{URL}/users", headers=auth(admin))).json()
    assert [s["status"] for s in listed] == ["past_due"]


async def test_canceled_after_the_end_stays_canceled(client, sessionmaker, member, plan):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    await client.put(f"{URL}/me/cancel", headers=auth(member))
    yesterday = shop_today() - timedelta(days=1)
    await move_dates(sessionmaker, member.id, start=yesterday - timedelta(days=30), end=yesterday)
    assert (await client.get(f"{URL}/me", headers=auth(member))).json()["status"] == "canceled"


# ── 3. mensalidade no caixa ─────────────────────────────


async def test_subscribing_records_the_monthly_fee(client, sessionmaker, member, plan):
    response = await subscribe(client, member, plan["id"], {"payment_method": "pix"})
    assert response.status_code == 201, response.text
    async with sessionmaker() as db:
        [fee] = (await db.execute(select(Transaction))).scalars().all()
    assert fee.type == TransactionType.SUBSCRIPTION
    assert fee.reference_id == uuid.UUID(response.json()["id"])
    assert (Decimal(fee.amount), fee.payment_method, fee.user_id) == (Decimal("89.90"), PaymentMethod.PIX, member.id)


async def test_default_payment_is_credit_card(client, sessionmaker, member, plan):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    async with sessionmaker() as db:
        fee = (await db.execute(select(Transaction))).scalar_one()
    assert fee.payment_method == PaymentMethod.CREDIT_CARD


async def test_renewal_records_another_fee(client, sessionmaker, member, plan):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    yesterday = shop_today() - timedelta(days=1)
    await move_dates(sessionmaker, member.id, start=yesterday - timedelta(days=30), end=yesterday)
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    assert await count(sessionmaker, Transaction) == 2


@pytest.mark.parametrize("body", [{"payment_method": "trim_club_credit"}, {"payment_method": "fiado"}])
async def test_invalid_payment_gets_422(client, sessionmaker, member, plan, body):
    assert (await subscribe(client, member, plan["id"], body)).status_code == 422
    assert await count(sessionmaker, UserSubscription) == 0
    assert await count(sessionmaker, Transaction) == 0


async def test_refused_subscription_records_no_fee(client, sessionmaker, member, plan):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    assert (await subscribe(client, member, plan["id"])).status_code == 400
    assert await count(sessionmaker, Transaction) == 1


# ── 4. só clientes ──────────────────────────────────────


@pytest.mark.parametrize("role", [UserRole.BARBER, UserRole.ADMIN])
async def test_staff_cannot_subscribe(client, sessionmaker, plan, role):
    staff = await add_user(sessionmaker, f"{role.value}@teste.com", role)
    response = await subscribe(client, staff, plan["id"])
    assert response.status_code == 403
    assert response.json()["detail"] == "Apenas clientes podem assinar o Trim Club."
    assert await count(sessionmaker, UserSubscription) == 0


# ── 5. dia da barbearia ─────────────────────────────────


async def test_start_date_uses_the_shop_day(client, member, plan, monkeypatch):
    """Às 22:00 de 25/11 em Brasília, o servidor em UTC já está em 26/11."""
    late = datetime(2026, 11, 25, 22, 0, tzinfo=BRT)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return late.astimezone(tz) if tz else late.replace(tzinfo=None)

    monkeypatch.setattr(subscription_service, "datetime", FixedDatetime)
    body = (await subscribe(client, member, plan["id"])).json()
    assert body["start_date"] == "2026-11-25"
    assert body["end_date"] == "2026-12-25"


# ── avisos (#75) ────────────────────────────────────────


async def test_subscribe_and_cancel_notify_the_member(client, sessionmaker, member, plan):
    assert (await subscribe(client, member, plan["id"])).status_code == 201
    assert (await client.put(f"{URL}/me/cancel", headers=auth(member))).status_code == 200
    async with sessionmaker() as db:
        notices = (await db.execute(select(Notification).order_by(Notification.created_at))).scalars().all()
    assert [(n.title, n.type) for n in notices] == [
        ("Bem-vindo ao Trim Club", NotificationType.SUBSCRIPTION_NOTICE),
        ("Assinatura cancelada", NotificationType.SUBSCRIPTION_NOTICE),
    ]
    assert "Clássico" in notices[0].message


# ── 6 a 8. planos ───────────────────────────────────────


@pytest.mark.parametrize(
    "field", ["name", "monthly_price", "included_cuts", "included_shaves", "discount_percentage", "is_active"]
)
async def test_put_plan_with_null_gets_422(client, sessionmaker, admin, plan, field):
    response = await client.put(f"{URL}/plans/{plan['id']}", json={field: None}, headers=auth(admin))
    assert response.status_code == 422
    async with sessionmaker() as db:
        saved = await db.get(SubscriptionPlan, uuid.UUID(plan["id"]))
    assert (saved.name, saved.is_active) == ("Clássico", True)


async def test_put_plan_can_clear_the_description(client, admin, plan):
    response = await client.put(f"{URL}/plans/{plan['id']}", json={"description": None}, headers=auth(admin))
    assert response.status_code == 200


@pytest.mark.parametrize("name", ["", "   "])
async def test_blank_plan_name_gets_422(client, sessionmaker, admin, plan, name):
    response = await client.post(f"{URL}/plans", json={"name": name, "monthly_price": 10}, headers=auth(admin))
    assert response.status_code == 422
    assert (await client.put(f"{URL}/plans/{plan['id']}", json={"name": name}, headers=auth(admin))).status_code == 422
    assert await count(sessionmaker, SubscriptionPlan) == 1


async def test_plan_name_is_unique_ignoring_case(client, admin, plan):
    response = await client.post(f"{URL}/plans", json={"name": "CLÁSSICO", "monthly_price": 10}, headers=auth(admin))
    assert response.status_code == 400
    own = await client.put(f"{URL}/plans/{plan['id']}", json={"name": "clássico"}, headers=auth(admin))
    assert own.status_code == 200


async def test_put_is_active_reactivates_the_plan(client, admin, plan):
    assert (await client.delete(f"{URL}/plans/{plan['id']}", headers=auth(admin))).status_code == 204
    assert (await client.get(f"{URL}/plans")).json() == []

    response = await client.put(f"{URL}/plans/{plan['id']}", json={"is_active": True}, headers=auth(admin))

    assert response.status_code == 200
    assert [p["id"] for p in (await client.get(f"{URL}/plans")).json()] == [plan["id"]]
