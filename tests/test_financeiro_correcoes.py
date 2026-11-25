"""
Financeiro: venda atômica, produto desativado, regras de cobrança, Trim Club, comissões pendentes,
extrato por data e 404 (#59).

Spec: SPEC/2026-11-25-financeiro-correcoes.md
"""

import uuid
from datetime import date, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.appointments.models import Appointment
from src.backend.modules.appointments.models import AppointmentStatus as S
from src.backend.modules.auth.models import UserRole
from src.backend.modules.finance.models import BarberCommission, PaymentMethod, Transaction, TransactionType
from src.backend.modules.products.models import InventoryMovement, Product
from src.backend.modules.subscriptions.models import SubscriptionPlan, SubscriptionStatus, UserSubscription
from tests.agenda_fixtures import brt, count, create_shop, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/finance"
NOW = brt(2026, 12, 1, 14, 0)  # terça, 14:00 em Brasília (17:00Z)


@pytest_asyncio.fixture
async def shop(sessionmaker, set_now):
    set_now(NOW)
    data = await create_shop(sessionmaker)
    data["admin"] = await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)
    return data


async def booking(maker, shop, *, status=S.CONFIRMED, start=None, price=Decimal("40.00")):
    start = start or NOW - timedelta(hours=1)
    async with maker() as db:
        appointment = Appointment(
            client_id=shop["client"].id, barber_id=shop["barber_id"], start_datetime=start,
            end_datetime=start + timedelta(minutes=30), status=status, total_price=price,
        )
        db.add(appointment)
        await db.commit()
        return appointment.id


async def charge(client, shop, appointment_id, method="cash"):
    return await client.post(
        f"{URL}/checkout/appointment/{appointment_id}", json={"payment_method": method}, headers=auth(shop["admin"])
    )


async def product(maker, *, stock=5, active=True):
    async with maker() as db:
        item = Product(name="Pomada", price=Decimal("25.00"), stock_quantity=stock, is_active=active)
        db.add(item)
        await db.commit()
        return item.id


async def sell(client, shop, product_id, **extra):
    body = {"product_id": str(product_id), "quantity": 1, "payment_method": "pix", **extra}
    return await client.post(f"{URL}/checkout/product", json=body, headers=auth(shop["admin"]))


async def stock_of(maker, product_id):
    async with maker() as db:
        return (await db.get(Product, product_id)).stock_quantity


async def subscribe(maker, user_id, *, status=SubscriptionStatus.ACTIVE, start=date(2026, 11, 20), end=date(2026, 12, 20)):
    async with maker() as db:
        plan = SubscriptionPlan(name=f"Plano {uuid.uuid4().hex[:6]}", monthly_price=Decimal("99.90"))
        db.add(plan)
        await db.flush()
        db.add(UserSubscription(user_id=user_id, plan_id=plan.id, start_date=start, end_date=end, status=status))
        await db.commit()


# ── 1. venda com cliente inexistente ────────────────────


async def test_sale_to_unknown_client_gets_404_and_keeps_the_stock(client, shop, sessionmaker):
    product_id = await product(sessionmaker)

    response = await sell(client, shop, product_id, user_id=str(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["detail"] == "Cliente não encontrado."
    assert await stock_of(sessionmaker, product_id) == 5
    assert await count(sessionmaker, InventoryMovement) == 0
    assert await count(sessionmaker, Transaction) == 0


async def test_sale_writes_stock_and_transaction_together(client, shop, sessionmaker):
    product_id = await product(sessionmaker)
    response = await sell(client, shop, product_id, user_id=str(shop["client"].id))
    assert response.status_code == 201, response.text
    assert await stock_of(sessionmaker, product_id) == 4
    assert await count(sessionmaker, InventoryMovement) == 1
    assert await count(sessionmaker, Transaction) == 1


# ── 2. produto desativado ───────────────────────────────


async def test_deactivated_product_cannot_be_sold(client, shop, sessionmaker):
    product_id = await product(sessionmaker, active=False)
    response = await sell(client, shop, product_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "Produto desativado não pode ser vendido."
    assert await stock_of(sessionmaker, product_id) == 5
    assert await count(sessionmaker, Transaction) == 0


# ── 3. regras de cobrança do agendamento ────────────────


async def test_pending_appointment_cannot_be_charged(client, shop, sessionmaker):
    appointment_id = await booking(sessionmaker, shop, status=S.PENDING)
    response = await charge(client, shop, appointment_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "Só é possível cobrar um agendamento confirmado."
    assert await count(sessionmaker, Transaction) == 0


async def test_appointment_that_has_not_started_cannot_be_charged(client, shop, sessionmaker):
    appointment_id = await booking(sessionmaker, shop, start=NOW + timedelta(days=1))
    response = await charge(client, shop, appointment_id)
    assert response.status_code == 400
    assert response.json()["detail"] == "Só é possível cobrar depois do início do agendamento."
    async with sessionmaker() as db:
        assert (await db.get(Appointment, appointment_id)).status == S.CONFIRMED


async def test_appointment_starting_now_can_be_charged(client, shop, sessionmaker):
    appointment_id = await booking(sessionmaker, shop, start=NOW)
    assert (await charge(client, shop, appointment_id)).status_code == 201


# ── 4. Trim Club ────────────────────────────────────────


async def test_trim_club_credit_needs_an_active_subscription(client, shop, sessionmaker):
    appointment_id = await booking(sessionmaker, shop)
    response = await charge(client, shop, appointment_id, "trim_club_credit")
    assert response.status_code == 400
    assert response.json()["detail"] == "O cliente não tem assinatura ativa do Trim Club."
    assert await count(sessionmaker, Transaction) == 0


async def test_trim_club_credit_with_active_subscription_is_free(client, shop, sessionmaker):
    await subscribe(sessionmaker, shop["client"].id)
    appointment_id = await booking(sessionmaker, shop)
    response = await charge(client, shop, appointment_id, "trim_club_credit")
    assert response.status_code == 201, response.text
    assert Decimal(response.json()["amount"]) == Decimal("0.00")


@pytest.mark.parametrize(
    "status, start, end",
    [
        (SubscriptionStatus.CANCELED, date(2026, 11, 20), date(2026, 12, 20)),
        (SubscriptionStatus.PAST_DUE, date(2026, 11, 20), date(2026, 12, 20)),
        (SubscriptionStatus.ACTIVE, date(2026, 10, 1), date(2026, 11, 30)),  # venceu ontem
        (SubscriptionStatus.ACTIVE, date(2026, 12, 2), date(2027, 1, 2)),  # começa amanhã
    ],
)
async def test_trim_club_credit_refused_without_a_valid_subscription_today(client, shop, sessionmaker, status, start, end):
    await subscribe(sessionmaker, shop["client"].id, status=status, start=start, end=end)
    appointment_id = await booking(sessionmaker, shop)
    assert (await charge(client, shop, appointment_id, "trim_club_credit")).status_code == 400


# ── 5. comissões pendentes e extrato por data ───────────


async def test_pending_commissions_grouped_by_barber(client, shop, sessionmaker):
    other = await add_barber(sessionmaker, "bia@teste.com", full_name="Bia Souza", commission_rate=40)
    first = await booking(sessionmaker, shop, price=Decimal("40.00"))
    second = await booking(sessionmaker, shop, price=Decimal("60.00"), start=NOW - timedelta(hours=3))
    async with sessionmaker() as db:
        third = Appointment(
            client_id=shop["client"].id, barber_id=other.id, start_datetime=NOW - timedelta(hours=2),
            end_datetime=NOW - timedelta(hours=1), status=S.CONFIRMED, total_price=Decimal("100.00"),
        )
        db.add(third)
        await db.commit()
    for appointment_id in (first, second, third.id):
        assert (await charge(client, shop, appointment_id)).status_code == 201
    # Uma comissão do barbeiro da casa já paga não entra no total pendente.
    async with sessionmaker() as db:
        paid = (await db.execute(
            select(BarberCommission).where(BarberCommission.barber_id == shop["barber_id"]).order_by(BarberCommission.amount)
        )).scalars().first()
    await client.put(
        f"{URL}/commissions/pay",
        json={"barber_id": str(shop["barber_id"]), "commission_ids": [str(paid.id)]},
        headers=auth(shop["admin"]),
    )

    response = await client.get(f"{URL}/commissions", headers=auth(shop["admin"]))

    assert response.status_code == 200
    assert [(c["barber_name"], c["pending_count"], Decimal(c["pending_amount"])) for c in response.json()] == [
        ("Bia Souza", 1, Decimal("40.00")),
        ("Barbeiro", 1, Decimal("30.00")),
    ]


async def test_pending_commissions_are_admin_only(client, shop):
    assert (await client.get(f"{URL}/commissions", headers=auth(shop["barber_user"]))).status_code == 403


async def statement_with_days(maker):
    """Três transações: 30/11 às 23:30, 1/12 às 00:30 e 1/12 às 21:30, horários de Brasília."""
    async with maker() as db:
        for local in (brt(2026, 11, 30, 23, 30), brt(2026, 12, 1, 0, 30), brt(2026, 12, 1, 21, 30)):
            db.add(Transaction(
                type=TransactionType.PRODUCT_SALE, reference_id=uuid.uuid4(), amount=Decimal("10.00"),
                payment_method=PaymentMethod.CASH,
                created_at=local.astimezone(timezone.utc),
            ))
        await db.commit()


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"start_date": "2026-12-01", "end_date": "2026-12-01"}, 2),
        ({"start_date": "2026-11-30", "end_date": "2026-11-30"}, 1),
        ({"start_date": "2026-12-01"}, 2),
        ({"end_date": "2026-11-30"}, 1),
        ({}, 3),
    ],
)
async def test_statement_filters_by_shop_day(client, shop, sessionmaker, params, expected):
    await statement_with_days(sessionmaker)
    response = await client.get(f"{URL}/transactions", params=params, headers=auth(shop["admin"]))
    assert response.status_code == 200
    assert len(response.json()) == expected


async def test_statement_with_inverted_period_gets_422(client, shop):
    params = {"start_date": "2026-12-02", "end_date": "2026-12-01"}
    response = await client.get(f"{URL}/transactions", params=params, headers=auth(shop["admin"]))
    assert response.status_code == 422


# ── 6. agendamento desconhecido ─────────────────────────


async def test_unknown_appointment_gets_404(client, shop):
    response = await charge(client, shop, uuid.uuid4())
    assert response.status_code == 404
    assert response.json()["detail"] == "Agendamento não encontrado."

