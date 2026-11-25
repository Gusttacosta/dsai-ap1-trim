"""
Testes de integração dos relatórios do painel (#3).

Spec: SPEC/2026-11-24-testes-integracao-dashboard.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Os dados são gravados direto no banco com datas fixas ao meio-dia UTC,
para o resultado não depender do fuso do servidor. Substituem o tests/test_dashboard.py gerado, que
não importava a aplicação.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

from src.backend.modules.appointments.models import Appointment
from src.backend.modules.appointments.models import AppointmentStatus as S
from src.backend.modules.auth.models import UserRole
from src.backend.modules.expenses.models import Expense
from src.backend.modules.finance.models import BarberCommission, PaymentMethod, Transaction, TransactionType
from tests.agenda_fixtures import needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/reports"
NOV = {"start_date": "2026-11-01", "end_date": "2026-11-30"}
ZERO = {"total_revenue": "0", "total_commissions": "0", "total_expenses": "0", "net_profit": "0"}


# ── apoio ───────────────────────────────────────────────


def noon(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


@pytest_asyncio.fixture
async def customer(sessionmaker):
    return await add_user(sessionmaker, "cliente@teste.com")


async def add_sale(maker, day, amount, kind=TransactionType.PRODUCT_SALE, user_id=None):
    async with maker() as db:
        transaction = Transaction(
            type=kind, reference_id=uuid.uuid4(), amount=amount, payment_method=PaymentMethod.PIX,
            user_id=user_id, created_at=noon(day),
        )
        db.add(transaction)
        await db.commit()
        return transaction.id


async def add_charged_service(maker, barber_id, day, amount, commission, *, paid=False):
    """Transação de agendamento e a comissão dela, no mesmo dia."""
    transaction_id = await add_sale(maker, day, amount, TransactionType.APPOINTMENT)
    async with maker() as db:
        db.add(BarberCommission(
            barber_id=barber_id, transaction_id=transaction_id, amount=commission, is_paid=paid,
            created_at=noon(day),
        ))
        await db.commit()


async def add_expense(maker, day, amount):
    async with maker() as db:
        db.add(Expense(description=f"Despesa {day}", amount=amount, payment_date=day))
        await db.commit()


async def add_appointment(maker, client_id, barber_id, start, status=S.COMPLETED):
    async with maker() as db:
        db.add(Appointment(
            client_id=client_id, barber_id=barber_id, start_datetime=start,
            end_datetime=start + timedelta(minutes=30), status=status, total_price=40,
        ))
        await db.commit()


async def summary(client, admin, **params):
    response = await client.get(f"{URL}/financial-summary", params=params, headers=auth(admin))
    assert response.status_code == 200, response.text
    return {k: Decimal(v) for k, v in response.json().items()}


async def overview(client, admin, **params):
    response = await client.get(f"{URL}/daily-overview", params=params, headers=auth(admin))
    assert response.status_code == 200, response.text
    return response.json()


def as_decimals(values):
    return {k: Decimal(v) for k, v in values.items()}


# ── resumo financeiro ───────────────────────────────────


async def test_summary_adds_revenue_commissions_and_expenses(client, admin, sessionmaker):
    barber = await add_barber(sessionmaker, "barbeiro@teste.com")
    await add_charged_service(sessionmaker, barber.id, date(2026, 11, 10), Decimal("100.00"), Decimal("50.00"))
    await add_charged_service(sessionmaker, barber.id, date(2026, 11, 12), Decimal("60.00"), Decimal("30.00"), paid=True)
    await add_sale(sessionmaker, date(2026, 11, 15), Decimal("25.50"))
    await add_sale(sessionmaker, date(2026, 11, 16), Decimal("99.90"), TransactionType.SUBSCRIPTION)
    await add_expense(sessionmaker, date(2026, 11, 5), Decimal("40.00"))

    assert await summary(client, admin, **NOV) == {
        "total_revenue": Decimal("285.40"),
        "total_commissions": Decimal("80.00"),
        "total_expenses": Decimal("40.00"),
        "net_profit": Decimal("165.40"),
    }


async def test_summary_includes_both_ends_and_nothing_outside(client, admin, sessionmaker):
    barber = await add_barber(sessionmaker, "barbeiro@teste.com")
    for day, amount in [(date(2026, 10, 31), "1000"), (date(2026, 11, 1), "10"), (date(2026, 11, 30), "20"),
                        (date(2026, 12, 1), "2000")]:
        await add_charged_service(sessionmaker, barber.id, day, Decimal(amount), Decimal(amount) / 2)
        await add_expense(sessionmaker, day, Decimal(amount) / 10)

    assert await summary(client, admin, **NOV) == {
        "total_revenue": Decimal("30.00"),
        "total_commissions": Decimal("15.00"),
        "total_expenses": Decimal("3.00"),
        "net_profit": Decimal("12.00"),
    }


async def test_summary_can_be_a_loss(client, admin, sessionmaker):
    await add_sale(sessionmaker, date(2026, 11, 10), Decimal("50.00"))
    await add_expense(sessionmaker, date(2026, 11, 10), Decimal("2500.00"))
    result = await summary(client, admin, **NOV)
    assert result["net_profit"] == Decimal("-2450.00")


async def test_summary_without_data_is_zero(client, admin):
    assert await summary(client, admin, **NOV) == as_decimals(ZERO)


async def test_summary_defaults_to_the_current_month(client, admin, sessionmaker):
    await add_sale(sessionmaker, date.today(), Decimal("70.00"))
    await add_sale(sessionmaker, date.today() - timedelta(days=62), Decimal("500.00"))
    await add_expense(sessionmaker, date.today(), Decimal("20.00"))
    result = await summary(client, admin)
    assert (result["total_revenue"], result["total_expenses"], result["net_profit"]) == (
        Decimal("70.00"), Decimal("20.00"), Decimal("50.00"),
    )


async def test_summary_invalid_date_gets_422(client, admin):
    response = await client.get(f"{URL}/financial-summary", params={"start_date": "novembro"}, headers=auth(admin))
    assert response.status_code == 422


# ── visão do dia ────────────────────────────────────────


async def test_overview_counts_the_days_appointments_by_status(client, admin, customer, sessionmaker):
    barber = await add_barber(sessionmaker, "barbeiro@teste.com")
    day = date(2026, 11, 10)
    for status, hour in [(S.COMPLETED, 12), (S.COMPLETED, 13), (S.NO_SHOW, 14), (S.CANCELLED, 15),
                         (S.CONFIRMED, 16), (S.PENDING, 17)]:
        await add_appointment(sessionmaker, customer.id, barber.id, noon(day).replace(hour=hour), status)
    await add_appointment(sessionmaker, customer.id, barber.id, noon(day + timedelta(days=1)))
    await add_appointment(sessionmaker, customer.id, barber.id, noon(day - timedelta(days=1)), S.NO_SHOW)

    body = await overview(client, admin, target_date="2026-11-10")
    assert (body["total_appointments"], body["completed_appointments"], body["no_show_appointments"],
            body["cancelled_appointments"]) == (6, 2, 1, 1)


async def test_overview_average_ticket_uses_only_the_days_appointment_charges(client, admin, sessionmaker):
    barber = await add_barber(sessionmaker, "barbeiro@teste.com")
    day = date(2026, 11, 10)
    for amount in ("40.00", "55.00", "70.00"):
        await add_charged_service(sessionmaker, barber.id, day, Decimal(amount), Decimal("1.00"))
    await add_sale(sessionmaker, day, Decimal("500.00"))
    await add_charged_service(sessionmaker, barber.id, day + timedelta(days=1), Decimal("900.00"), Decimal("1.00"))

    body = await overview(client, admin, target_date="2026-11-10")
    assert Decimal(body["ticket_medio"]) == Decimal("55.00")


async def test_overview_ticket_is_rounded_to_cents(client, admin, sessionmaker):
    barber = await add_barber(sessionmaker, "barbeiro@teste.com")
    for amount in ("10.00", "10.00", "10.01"):
        await add_charged_service(sessionmaker, barber.id, date(2026, 11, 10), Decimal(amount), Decimal("1.00"))
    body = await overview(client, admin, target_date="2026-11-10")
    assert Decimal(body["ticket_medio"]) == Decimal("10.00")


async def test_overview_without_data_is_zero(client, admin):
    assert await overview(client, admin, target_date="2026-11-10") == {
        "total_appointments": 0, "completed_appointments": 0, "no_show_appointments": 0,
        "cancelled_appointments": 0, "ticket_medio": "0.00",
    }


async def test_overview_defaults_to_today(client, admin, customer, sessionmaker):
    barber = await add_barber(sessionmaker, "barbeiro@teste.com")
    await add_appointment(sessionmaker, customer.id, barber.id, noon(date.today()), S.CONFIRMED)
    await add_appointment(sessionmaker, customer.id, barber.id, noon(date.today() - timedelta(days=3)))
    body = await overview(client, admin)
    assert (body["total_appointments"], body["completed_appointments"]) == (1, 0)
