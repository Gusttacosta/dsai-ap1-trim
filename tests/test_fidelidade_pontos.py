"""
Pontos de fidelidade gerados pelos pagamentos (#13): 1 ponto por real pago.

Spec: SPEC/2026-11-25-fidelidade-pontos.md
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.appointments.models import Appointment
from src.backend.modules.appointments.models import AppointmentStatus as S
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.loyalty.models import LoyaltyWallet
from src.backend.modules.loyalty.service import points_for
from src.backend.modules.notifications.models import Notification, NotificationType
from src.backend.modules.products.models import Product
from src.backend.modules.subscriptions.models import SubscriptionPlan, SubscriptionStatus, UserSubscription
from tests.agenda_fixtures import brt, count, create_shop, needs_db
from tests.api_helpers import add_user, auth

NOW = brt(2026, 12, 1, 14, 0)


def test_one_point_per_real_without_cents():
    assert [points_for(v) for v in (Decimal("40.00"), Decimal("39.99"), Decimal("0.99"), 0, None)] == [40, 39, 0, 0, 0]




@pytest_asyncio.fixture
async def shop(sessionmaker, set_now):
    set_now(NOW)
    data = await create_shop(sessionmaker)
    data["admin"] = await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)
    return data


async def started_booking(maker, shop, price="45.90", client_id=None):
    start = NOW - timedelta(hours=1)
    async with maker() as db:
        a = Appointment(client_id=client_id or shop["client"].id, barber_id=shop["barber_id"], start_datetime=start,
                        end_datetime=start + timedelta(minutes=30), status=S.CONFIRMED, total_price=Decimal(price))
        db.add(a)
        await db.commit()
        return a.id


async def wallet_of(maker, user_id):
    async with maker() as db:
        return (await db.execute(select(LoyaltyWallet).where(LoyaltyWallet.user_id == user_id))).scalar_one_or_none()


async def loyalty_notices(maker, user_id):
    async with maker() as db:
        rows = await db.execute(select(Notification.title).where(
            Notification.user_id == user_id, Notification.type == NotificationType.LOYALTY_UPDATE))
        return list(rows.scalars().all())


@pytest.mark.asyncio
@needs_db
async def test_barber_completing_gives_points(client, sessionmaker, shop, set_now):
    appointment_id = await started_booking(sessionmaker, shop)
    response = await client.put(f"/api/appointments/{appointment_id}/status", json={"status": "completed"},
                                headers=auth(shop["barber_user"]))
    assert response.status_code == 200, response.text

    wallet = await wallet_of(sessionmaker, shop["client"].id)
    assert (wallet.balance, wallet.lifetime_points) == (45, 45)
    assert await loyalty_notices(sessionmaker, shop["client"].id) == ["Você ganhou pontos"]


@pytest.mark.asyncio
@needs_db
async def test_cashier_checkout_gives_points_once(client, sessionmaker, shop):
    appointment_id = await started_booking(sessionmaker, shop, "60.00")
    url = f"/api/finance/checkout/appointment/{appointment_id}"
    assert (await client.post(url, json={"payment_method": "pix"}, headers=auth(shop["admin"]))).status_code == 201
    assert (await client.post(url, json={"payment_method": "pix"}, headers=auth(shop["admin"]))).status_code == 400
    assert (await wallet_of(sessionmaker, shop["client"].id)).balance == 60


@pytest.mark.asyncio
@needs_db
async def test_trim_club_credit_gives_no_points(client, sessionmaker, shop):
    async with sessionmaker() as db:
        plan = SubscriptionPlan(name="Clube", monthly_price=Decimal("99.90"))
        db.add(plan)
        await db.flush()
        db.add(UserSubscription(user_id=shop["client"].id, plan_id=plan.id, start_date=date(2026, 11, 20),
                                end_date=date(2026, 12, 20), status=SubscriptionStatus.ACTIVE))
        await db.commit()
    appointment_id = await started_booking(sessionmaker, shop)
    response = await client.post(f"/api/finance/checkout/appointment/{appointment_id}",
                                 json={"payment_method": "trim_club_credit"}, headers=auth(shop["admin"]))
    assert response.status_code == 201, response.text
    assert await wallet_of(sessionmaker, shop["client"].id) is None


@pytest.mark.asyncio
@needs_db
async def test_product_sale_to_a_client_gives_points(client, sessionmaker, shop):
    async with sessionmaker() as db:
        item = Product(name="Pomada", price=Decimal("25.50"), stock_quantity=5)
        db.add(item)
        await db.commit()
    body = {"product_id": str(item.id), "quantity": 2, "payment_method": "cash", "user_id": str(shop["client"].id)}
    assert (await client.post("/api/finance/checkout/product", json=body, headers=auth(shop["admin"]))).status_code == 201
    assert (await wallet_of(sessionmaker, shop["client"].id)).balance == 51

    anonymous = {k: v for k, v in body.items() if k != "user_id"}
    assert (await client.post("/api/finance/checkout/product", json=anonymous, headers=auth(shop["admin"]))).status_code == 201
    assert await count(sessionmaker, LoyaltyWallet) == 1


@pytest.mark.asyncio
@needs_db
async def test_points_add_to_an_existing_wallet(client, sessionmaker, shop):
    async with sessionmaker() as db:
        db.add(LoyaltyWallet(user_id=shop["client"].id, balance=10, lifetime_points=50))
        await db.commit()
    appointment_id = await started_booking(sessionmaker, shop, "30.00")
    await client.post(f"/api/finance/checkout/appointment/{appointment_id}", json={"payment_method": "cash"},
                      headers=auth(shop["admin"]))
    wallet = await wallet_of(sessionmaker, shop["client"].id)
    assert (wallet.balance, wallet.lifetime_points) == (40, 80)


@pytest.mark.asyncio
@needs_db
async def test_inactive_client_gets_no_points(client, sessionmaker, shop):
    ghost = await add_user(sessionmaker, f"{uuid.uuid4().hex[:6]}@trim.local", is_active=False)
    appointment_id = await started_booking(sessionmaker, shop, client_id=ghost.id)
    response = await client.post(f"/api/finance/checkout/appointment/{appointment_id}",
                                 json={"payment_method": "cash"}, headers=auth(shop["admin"]))
    assert response.status_code == 201
    assert await wallet_of(sessionmaker, ghost.id) is None


@pytest.mark.asyncio
@needs_db
async def test_points_can_be_redeemed_in_the_catalog(client, sessionmaker, shop):
    appointment_id = await started_booking(sessionmaker, shop, "80.00")
    await client.post(f"/api/finance/checkout/appointment/{appointment_id}", json={"payment_method": "cash"},
                      headers=auth(shop["admin"]))
    reward = (await client.post("/api/loyalty/rewards", json={"name": "Pomada", "points_cost": 80},
                                headers=auth(shop["admin"]))).json()

    response = await client.post(f"/api/loyalty/redeem/{reward['id']}", headers=auth(shop["client"]))

    assert response.status_code == 201, response.text
    assert (await client.get("/api/loyalty/me", headers=auth(shop["client"]))).json()["balance"] == 0
    assert sorted(await loyalty_notices(sessionmaker, shop["client"].id)) == ["Resgate confirmado", "Você ganhou pontos"]
    async with sessionmaker() as db:
        assert (await db.get(User, shop["client"].id)).is_active
