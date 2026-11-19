"""
Testes do cancelamento de agendamento pelo cliente (#24).

Spec: SPEC/2026-11-18-cancelamento-agendamento.md

Usam o PostgreSQL de TEST_DATABASE_URL e "agora" fixo (ver tests/agenda_fixtures.py).
"""

import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.main import app
from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.appointments.service import AppointmentService
from src.backend.modules.auth.dependencies import get_current_user
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.finance.models import BarberCommission, Transaction
from tests.agenda_fixtures import brt, count, create_shop, needs_db

pytestmark = [pytest.mark.asyncio, needs_db]

NOW = brt(2026, 11, 8, 14, 0)
NOT_FOUND = "Agendamento não encontrado."


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def shop(sessionmaker, set_now):
    set_now(NOW)
    return await create_shop(sessionmaker)


async def add_appointment(maker, shop, *, start, status=AppointmentStatus.CONFIRMED, client_id=None):
    async with maker() as db:
        appointment = Appointment(
            client_id=client_id or shop["client"].id,
            barber_id=shop["barber_id"],
            start_datetime=start,
            end_datetime=start + timedelta(minutes=30),
            status=status,
            total_price=40,
        )
        db.add(appointment)
        await db.commit()
        return appointment.id


async def other_client(maker):
    async with maker() as db:
        user = User(email="outro@teste.com", hashed_password="x", full_name="Outro", role=UserRole.CLIENT)
        db.add(user)
        await db.commit()
        return user


async def status_in_db(maker, appointment_id):
    async with maker() as db:
        return (await db.execute(select(Appointment.status).where(Appointment.id == appointment_id))).scalar_one()


async def cancel_as(client, user, appointment_id):
    app.dependency_overrides[get_current_user] = lambda: user
    return await client.put(f"/api/appointments/{appointment_id}/cancel")


@pytest.mark.parametrize("status", [AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING])
async def test_owner_cancels_active_future_appointment(client, sessionmaker, shop, status):
    appointment_id = await add_appointment(sessionmaker, shop, start=brt(2026, 11, 9, 10, 0), status=status)

    response = await cancel_as(client, shop["client"], appointment_id)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert await status_in_db(sessionmaker, appointment_id) == AppointmentStatus.CANCELLED


async def test_other_client_gets_404_and_nothing_changes(client, sessionmaker, shop):
    appointment_id = await add_appointment(sessionmaker, shop, start=brt(2026, 11, 9, 10, 0))
    intruder = await other_client(sessionmaker)

    response = await cancel_as(client, intruder, appointment_id)

    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND
    assert await status_in_db(sessionmaker, appointment_id) == AppointmentStatus.CONFIRMED


async def test_unknown_id_gets_404(client, sessionmaker, shop):
    response = await cancel_as(client, shop["client"], uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


@pytest.mark.parametrize("start", [NOW, NOW - timedelta(minutes=10), brt(2026, 11, 7, 10, 0)])
async def test_started_or_past_appointment_cannot_be_cancelled(client, sessionmaker, shop, start):
    appointment_id = await add_appointment(sessionmaker, shop, start=start)

    response = await cancel_as(client, shop["client"], appointment_id)

    assert response.status_code == 400
    assert "já começou" in response.json()["detail"]
    assert await status_in_db(sessionmaker, appointment_id) == AppointmentStatus.CONFIRMED


@pytest.mark.parametrize("status", [AppointmentStatus.NO_SHOW, AppointmentStatus.CANCELLED])
async def test_inactive_appointment_cannot_be_cancelled(client, sessionmaker, shop, status):
    appointment_id = await add_appointment(sessionmaker, shop, start=brt(2026, 11, 9, 10, 0), status=status)

    response = await cancel_as(client, shop["client"], appointment_id)

    assert response.status_code == 400
    assert "pendentes ou confirmados" in response.json()["detail"]
    assert await status_in_db(sessionmaker, appointment_id) == status


async def test_completed_appointment_keeps_status_and_finance(client, sessionmaker, shop):
    appointment_id = await add_appointment(sessionmaker, shop, start=brt(2026, 11, 9, 10, 0))
    async with sessionmaker() as db:
        await AppointmentService(db).update_status(appointment_id, AppointmentStatus.COMPLETED)

    response = await cancel_as(client, shop["client"], appointment_id)

    assert response.status_code == 400
    assert await status_in_db(sessionmaker, appointment_id) == AppointmentStatus.COMPLETED
    assert await count(sessionmaker, Transaction) == 1
    assert await count(sessionmaker, BarberCommission) == 1


async def test_cancel_requires_authentication(client, sessionmaker, shop):
    appointment_id = await add_appointment(sessionmaker, shop, start=brt(2026, 11, 9, 10, 0))

    response = await client.put(f"/api/appointments/{appointment_id}/cancel")

    assert response.status_code in (401, 403)
    assert await status_in_db(sessionmaker, appointment_id) == AppointmentStatus.CONFIRMED
