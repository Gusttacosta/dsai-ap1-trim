"""
Testes do agendamento no fuso da barbearia (#12).

Spec: SPEC/2026-11-18-agendamento-fuso-horario.md

"Agora" é fixado substituindo `utc_now` no módulo do serviço, então os testes não
dependem da hora em que a CI roda. Os testes precisam de um PostgreSQL em
TEST_DATABASE_URL (ver tests/agenda_fixtures.py). Sem essa variável, são pulados.
"""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from src.backend.config import settings
from src.backend.main import app
from src.backend.modules.appointments import service as appointment_service
from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.auth.dependencies import get_current_user
from src.backend.modules.auth.models import User
from tests.agenda_fixtures import BRT, brt, count, create_shop, needs_db

pytestmark = [pytest.mark.asyncio, needs_db]


@pytest.fixture(autouse=True)
def shop_settings(monkeypatch):
    monkeypatch.setattr(settings, "shop_timezone", "America/Sao_Paulo", raising=False)
    monkeypatch.setattr(settings, "booking_min_lead_minutes", 0, raising=False)
    monkeypatch.setattr(settings, "booking_max_days_ahead", 30, raising=False)
    yield
    app.dependency_overrides.clear()


async def availability(client, shop, target_date):
    response = await client.get(
        "/api/appointments/availability",
        params={"barber_id": str(shop["barber_id"]), "target_date": target_date, "duration_minutes": 30},
    )
    assert response.status_code == 200, response.text
    return response.json()["available_slots"]


async def book_as_guest(client, shop, start_datetime):
    return await client.post(
        "/api/appointments/guest",
        json={
            "barber_id": str(shop["barber_id"]),
            "service_ids": [str(shop["service_id"])],
            "start_datetime": start_datetime,
            "guest_name": "Visitante Teste",
        },
    )


async def stored_starts(maker):
    async with maker() as db:
        result = await db.execute(select(Appointment.start_datetime))
        return [dt.astimezone(timezone.utc) for dt in result.scalars().all()]


# ── Disponibilidade ──────────────────────────────────────


async def test_availability_today_starts_after_now(client, sessionmaker, set_now):
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 14, 10))

    slots = await availability(client, shop, "2026-11-08")

    assert slots[0] == "14:30"
    assert slots[-1] == "17:30"


async def test_availability_after_21h_uses_local_date(client, sessionmaker, set_now):
    """O caso da #12: às 22h de Brasília já é o dia seguinte em UTC."""
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 22, 0))

    assert await availability(client, shop, "2026-11-08") == []
    assert (await availability(client, shop, "2026-11-09"))[0] == "09:00"


@pytest.mark.parametrize("target_date", ["2026-11-07", "2026-12-09"])
async def test_availability_outside_booking_window_is_empty(client, sessionmaker, set_now, target_date):
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 10, 0))

    assert await availability(client, shop, target_date) == []


async def test_availability_last_day_of_window_is_open(client, sessionmaker, set_now):
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 10, 0))

    assert (await availability(client, shop, "2026-12-08"))[0] == "09:00"


async def test_availability_lunch_is_in_local_time(client, sessionmaker, set_now):
    shop = await create_shop(sessionmaker, lunch=("12:00", "13:00"))
    set_now(brt(2026, 11, 8, 10, 0))

    slots = await availability(client, shop, "2026-11-09")

    assert "11:30" in slots
    assert "12:00" not in slots
    assert "12:30" not in slots
    assert "13:00" in slots


async def test_late_booking_blocks_its_own_local_day(client, sessionmaker, set_now):
    """21:30 em Brasília é 00:30 UTC do dia seguinte, mas ocupa o horário do próprio dia."""
    shop = await create_shop(sessionmaker, end="22:00")
    set_now(brt(2026, 11, 8, 10, 0))
    async with sessionmaker() as db:
        db.add(
            Appointment(
                client_id=shop["client"].id,
                barber_id=shop["barber_id"],
                start_datetime=datetime(2026, 11, 10, 0, 30, tzinfo=timezone.utc),
                end_datetime=datetime(2026, 11, 10, 1, 0, tzinfo=timezone.utc),
                status=AppointmentStatus.CONFIRMED,
                total_price=40,
            )
        )
        await db.commit()

    assert "21:30" not in await availability(client, shop, "2026-11-09")
    assert "21:30" in await availability(client, shop, "2026-11-10")


# ── Criação ──────────────────────────────────────────────


async def test_naive_start_is_read_in_shop_timezone(client, sessionmaker, set_now):
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 22, 0))

    response = await book_as_guest(client, shop, "2026-11-09T16:30:00")

    assert response.status_code == 201, response.text
    assert await stored_starts(sessionmaker) == [datetime(2026, 11, 9, 19, 30, tzinfo=timezone.utc)]
    returned = datetime.fromisoformat(response.json()["start_datetime"])
    assert returned.astimezone(BRT) == brt(2026, 11, 9, 16, 30)


async def test_aware_start_is_converted_to_utc(client, sessionmaker, set_now):
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 22, 0))

    response = await book_as_guest(client, shop, "2026-11-09T16:30:00-03:00")

    assert response.status_code == 201, response.text
    assert await stored_starts(sessionmaker) == [datetime(2026, 11, 9, 19, 30, tzinfo=timezone.utc)]


async def test_work_schedule_uses_local_weekday(client, sessionmaker, set_now):
    """Sábado 21:30 em Brasília é domingo 00:30 UTC; vale o expediente de sábado."""
    saturday = 6
    shop = await create_shop(sessionmaker, days=[saturday], end="22:00")
    set_now(brt(2026, 11, 2, 10, 0))

    response = await book_as_guest(client, shop, "2026-11-08T00:30:00Z")

    assert response.status_code == 201, response.text


@pytest.mark.parametrize("start", ["2026-11-08T16:30:00", "2026-11-08T22:00:00"])
async def test_guest_cannot_book_in_the_past(client, sessionmaker, set_now, start):
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 22, 0))
    users_before = await count(sessionmaker, User)

    response = await book_as_guest(client, shop, start)

    assert response.status_code == 400
    assert "já passou" in response.json()["detail"]
    assert await count(sessionmaker, Appointment) == 0
    assert await count(sessionmaker, User) == users_before


async def test_client_cannot_book_in_the_past(client, sessionmaker, set_now):
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 22, 0))
    app.dependency_overrides[get_current_user] = lambda: shop["client"]

    response = await client.post(
        "/api/appointments",
        json={
            "barber_id": str(shop["barber_id"]),
            "service_ids": [str(shop["service_id"])],
            "start_datetime": "2026-11-08T16:30:00",
        },
    )

    assert response.status_code == 400
    assert "já passou" in response.json()["detail"]
    assert await count(sessionmaker, Appointment) == 0


async def test_cannot_book_beyond_max_days_ahead(client, sessionmaker, set_now):
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 10, 0))

    too_far = await book_as_guest(client, shop, "2026-12-09T10:00:00")
    last_day = await book_as_guest(client, shop, "2026-12-08T10:00:00")

    assert too_far.status_code == 400
    assert last_day.status_code == 201, last_day.text


async def test_min_lead_minutes_blocks_slots_too_close(client, sessionmaker, set_now, monkeypatch):
    monkeypatch.setattr(settings, "booking_min_lead_minutes", 60)
    shop = await create_shop(sessionmaker)
    set_now(brt(2026, 11, 8, 14, 10))

    assert (await availability(client, shop, "2026-11-08"))[0] == "15:30"
    assert (await book_as_guest(client, shop, "2026-11-08T15:00:00")).status_code == 400


async def test_shop_timezone_is_configurable(client, sessionmaker, set_now, monkeypatch):
    monkeypatch.setattr(settings, "shop_timezone", "UTC")
    shop = await create_shop(sessionmaker)
    set_now(datetime(2026, 11, 8, 10, 0, tzinfo=timezone.utc))

    response = await book_as_guest(client, shop, "2026-11-09T16:30:00")

    assert response.status_code == 201, response.text
    assert await stored_starts(sessionmaker) == [datetime(2026, 11, 9, 16, 30, tzinfo=timezone.utc)]


async def test_service_accepts_injected_clock():
    moment = datetime(2026, 11, 9, 1, 0, tzinfo=timezone.utc)
    service = appointment_service.AppointmentService(db=None, now=lambda: moment)

    assert service.local_today() == date(2026, 11, 8)
