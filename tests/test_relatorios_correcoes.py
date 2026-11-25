"""
Relatórios: faturamento do dia, fuso da barbearia, ranking só com ativos, ocupação, período
invertido e ranking sem N+1 (#67).

Spec: SPEC/2026-11-25-relatorios.md
"""

import uuid
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy import event, update

from src.backend.modules.appointments.models import Appointment
from src.backend.modules.appointments.models import AppointmentStatus as S
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber, WorkSchedule
from src.backend.modules.dashboard import service as dashboard_service
from src.backend.modules.finance.models import BarberCommission, PaymentMethod, Transaction, TransactionType
from tests.agenda_fixtures import needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/reports"
BRT = ZoneInfo("America/Sao_Paulo")


def brt(y, m, d, h=12, minute=0):
    return datetime(y, m, d, h, minute, tzinfo=BRT)


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


@pytest_asyncio.fixture
async def customer(sessionmaker):
    return await add_user(sessionmaker, "cliente@teste.com")


async def sale(maker, when, amount, kind=TransactionType.PRODUCT_SALE):
    async with maker() as db:
        t = Transaction(type=kind, reference_id=uuid.uuid4(), amount=Decimal(amount), payment_method=PaymentMethod.PIX,
                        created_at=when.astimezone(timezone.utc))
        db.add(t)
        await db.commit()
        return t.id


async def charged(maker, barber_id, when, amount, commission):
    transaction_id = await sale(maker, when, amount, TransactionType.APPOINTMENT)
    async with maker() as db:
        db.add(BarberCommission(barber_id=barber_id, transaction_id=transaction_id, amount=Decimal(commission),
                                created_at=when.astimezone(timezone.utc)))
        await db.commit()


async def appointment(maker, client_id, barber_id, start, status=S.COMPLETED, minutes=30):
    async with maker() as db:
        db.add(Appointment(client_id=client_id, barber_id=barber_id, start_datetime=start.astimezone(timezone.utc),
                           end_datetime=(start + timedelta(minutes=minutes)).astimezone(timezone.utc),
                           status=status, total_price=40))
        await db.commit()


async def schedule(maker, barber_id, day_of_week, start="09:00", end="18:00", lunch=None, working=True):
    async with maker() as db:
        db.add(WorkSchedule(
            barber_id=barber_id, day_of_week=day_of_week, start_time=time.fromisoformat(start),
            end_time=time.fromisoformat(end), is_working=working,
            break_start=time.fromisoformat(lunch[0]) if lunch else None,
            break_end=time.fromisoformat(lunch[1]) if lunch else None,
        ))
        await db.commit()


async def get(client, admin, path, **params):
    response = await client.get(f"{URL}{path}", params=params, headers=auth(admin))
    assert response.status_code == 200, response.text
    return response.json()


# ── 1. faturamento do dia ───────────────────────────────


async def test_daily_overview_returns_the_days_revenue(client, sessionmaker, admin):
    await sale(sessionmaker, brt(2026, 11, 10, 10), "25.00")
    await sale(sessionmaker, brt(2026, 11, 10, 15), "40.50", TransactionType.APPOINTMENT)
    await sale(sessionmaker, brt(2026, 11, 11, 10), "999.00")
    body = await get(client, admin, "/daily-overview", target_date="2026-11-10")
    assert Decimal(body["total_revenue"]) == Decimal("65.50")


# ── 2. fuso da barbearia ────────────────────────────────


async def test_late_evening_counts_on_the_shop_day(client, sessionmaker, admin, customer):
    """22:00 de 10/11 em Brasília é 01:00Z de 11/11: conta no dia 10."""
    barber = await add_barber(sessionmaker, "bia@teste.com")
    await appointment(sessionmaker, customer.id, barber.id, brt(2026, 11, 10, 22))
    await charged(sessionmaker, barber.id, brt(2026, 11, 10, 22), "60.00", "30.00")

    day10 = await get(client, admin, "/daily-overview", target_date="2026-11-10")
    day11 = await get(client, admin, "/daily-overview", target_date="2026-11-11")
    assert (day10["total_appointments"], Decimal(day10["total_revenue"])) == (1, Decimal("60.00"))
    assert (day11["total_appointments"], Decimal(day11["total_revenue"])) == (0, Decimal("0"))


async def test_month_end_evening_stays_in_its_month(client, sessionmaker, admin):
    """Cobrança às 21:30 de 30/11 em Brasília (00:30Z de 1/12) é de novembro."""
    await sale(sessionmaker, brt(2026, 11, 30, 21, 30), "100.00")
    nov = await get(client, admin, "/financial-summary", start_date="2026-11-01", end_date="2026-11-30")
    dec = await get(client, admin, "/financial-summary", start_date="2026-12-01", end_date="2026-12-31")
    assert (Decimal(nov["total_revenue"]), Decimal(dec["total_revenue"])) == (Decimal("100.00"), Decimal("0"))


async def test_defaults_use_the_shop_today(client, sessionmaker, admin, monkeypatch):
    """Às 22:00 de 30/11 em Brasília, "hoje" é 30/11 e o mês é novembro, mesmo com o servidor em 1/12."""
    monkeypatch.setattr(dashboard_service, "utc_now", lambda: brt(2026, 11, 30, 22).astimezone(timezone.utc))
    await sale(sessionmaker, brt(2026, 11, 30, 9), "10.00")
    await sale(sessionmaker, brt(2026, 12, 1, 9), "500.00")
    summary = await get(client, admin, "/financial-summary")
    overview = await get(client, admin, "/daily-overview")
    assert Decimal(summary["total_revenue"]) == Decimal("10.00")
    assert Decimal(overview["total_revenue"]) == Decimal("10.00")


# ── 3. ranking só com barbeiros ativos ──────────────────


@pytest.mark.parametrize("what", ["perfil", "conta"])
async def test_ranking_leaves_out_deactivated_barbers(client, sessionmaker, admin, what):
    ana = await add_barber(sessionmaker, "ana@teste.com", full_name="Ana")
    await add_barber(sessionmaker, "bia@teste.com", full_name="Bia")
    await charged(sessionmaker, ana.id, brt(2026, 11, 10), "80.00", "40.00")
    async with sessionmaker() as db:
        if what == "perfil":
            await db.execute(update(Barber).where(Barber.id == ana.id).values(is_active=False))
        else:
            await db.execute(update(User).where(User.id == ana.user_id).values(is_active=False))
        await db.commit()
    body = await get(client, admin, "/barber-ranking", start_date="2026-11-01", end_date="2026-11-30")
    assert [p["barber_name"] for p in body] == ["Bia"]


async def test_ranking_ties_are_ordered_by_name(client, sessionmaker, admin):
    for name in ("Caio", "Ana", "Bia"):
        await add_barber(sessionmaker, f"{name.lower()}@teste.com", full_name=name)
    body = await get(client, admin, "/barber-ranking", start_date="2026-11-01", end_date="2026-11-30")
    assert [p["barber_name"] for p in body] == ["Ana", "Bia", "Caio"]


async def test_ranking_runs_a_fixed_number_of_queries(client, sessionmaker, admin):
    """Antes eram 3 consultas por barbeiro (N+1)."""
    for i in range(6):
        barber = await add_barber(sessionmaker, f"b{i}@teste.com", full_name=f"B{i}")
        await charged(sessionmaker, barber.id, brt(2026, 11, 10), f"{10 + i}.00", "1.00")

    statements = []
    engine = None
    async with sessionmaker() as db:
        engine = db.bind
    listener = lambda *args: statements.append(args[2])  # noqa: E731
    event.listen(engine.sync_engine, "before_cursor_execute", listener)
    try:
        body = await get(client, admin, "/barber-ranking", start_date="2026-11-01", end_date="2026-11-30")
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", listener)
    assert [p["barber_name"] for p in body] == [f"B{i}" for i in reversed(range(6))]
    ranking_queries = [s for s in statements if "barber" in s.lower()]
    assert len(ranking_queries) <= 5


# ── 4. ocupação ─────────────────────────────────────────


async def test_occupancy_of_the_day(client, sessionmaker, admin, customer):
    """Quarta, 11/11: Ana trabalha 09:00–18:00 com 1 h de almoço (480 min); Bia, 09:00–13:00
    (240 min); Caio está de folga. 3 h agendadas (pendente, confirmado e concluído) = 25%."""
    ana = await add_barber(sessionmaker, "ana@teste.com")
    bia = await add_barber(sessionmaker, "bia@teste.com")
    caio = await add_barber(sessionmaker, "caio@teste.com")
    wednesday = 3
    await schedule(sessionmaker, ana.id, wednesday, lunch=("12:00", "13:00"))
    await schedule(sessionmaker, bia.id, wednesday, end="13:00")
    await schedule(sessionmaker, caio.id, wednesday, working=False)
    await appointment(sessionmaker, customer.id, ana.id, brt(2026, 11, 11, 9), S.COMPLETED, minutes=60)
    await appointment(sessionmaker, customer.id, ana.id, brt(2026, 11, 11, 14), S.CONFIRMED, minutes=60)
    await appointment(sessionmaker, customer.id, bia.id, brt(2026, 11, 11, 10), S.PENDING, minutes=60)
    await appointment(sessionmaker, customer.id, bia.id, brt(2026, 11, 11, 11), S.CANCELLED, minutes=60)
    await appointment(sessionmaker, customer.id, bia.id, brt(2026, 11, 11, 12), S.NO_SHOW, minutes=30)

    body = await get(client, admin, "/daily-overview", target_date="2026-11-11")

    assert (body["booked_minutes"], body["available_minutes"]) == (180, 720)
    assert Decimal(body["occupancy_rate"]) == Decimal("25.00")


async def test_occupancy_without_schedules_is_zero(client, admin):
    body = await get(client, admin, "/daily-overview", target_date="2026-11-11")
    assert (body["available_minutes"], Decimal(body["occupancy_rate"])) == (0, Decimal("0"))


async def test_inactive_barbers_do_not_count_as_available(client, sessionmaker, admin):
    ana = await add_barber(sessionmaker, "ana@teste.com", is_active=False)
    await schedule(sessionmaker, ana.id, 3)
    body = await get(client, admin, "/daily-overview", target_date="2026-11-11")
    assert body["available_minutes"] == 0


# ── 5. período invertido ────────────────────────────────


@pytest.mark.parametrize("path", ["/financial-summary", "/barber-ranking"])
async def test_inverted_period_gets_422(client, admin, path):
    params = {"start_date": "2026-11-30", "end_date": "2026-11-01"}
    response = await client.get(f"{URL}{path}", params=params, headers=auth(admin))
    assert response.status_code == 422
    assert response.json()["detail"] == "A data inicial não pode ser depois da data final."


async def test_inverted_period_on_me_gets_422(client, sessionmaker):
    barber = await add_barber(sessionmaker, "ana@teste.com")
    async with sessionmaker() as db:
        user = await db.get(User, barber.user_id)
    params = {"start_date": "2026-11-30", "end_date": "2026-11-01"}
    assert (await client.get(f"{URL}/me", params=params, headers=auth(user))).status_code == 422
