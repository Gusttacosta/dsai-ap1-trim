"""
Testes da mudança de status pelo barbeiro e pelo admin (#26).

Spec: SPEC/2026-11-18-status-agendamento.md

Usam o PostgreSQL de TEST_DATABASE_URL e "agora" fixo (ver tests/agenda_fixtures.py).
"""

import uuid
from datetime import timedelta

import pytest
import pytest_asyncio

from src.backend.main import app
from src.backend.modules.appointments.models import AppointmentStatus as S
from src.backend.modules.auth.dependencies import get_current_user
from src.backend.modules.auth.models import UserRole
from src.backend.modules.barbers.models import Barber
from src.backend.modules.finance.models import BarberCommission, PaymentMethod, Transaction, TransactionType
from tests.agenda_fixtures import add_appointment, add_user, brt, count, create_shop, needs_db, status_in_db

pytestmark = [pytest.mark.asyncio, needs_db]

NOW = brt(2026, 11, 8, 14, 0)
PAST = NOW - timedelta(minutes=30)
FUTURE = NOW + timedelta(hours=2)
FINAL = [S.COMPLETED, S.NO_SHOW, S.CANCELLED]


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def shop(sessionmaker, set_now):
    set_now(NOW)
    return await create_shop(sessionmaker)


async def change_as(client, user, appointment_id, new_status):
    app.dependency_overrides[get_current_user] = lambda: user
    return await client.put(f"/api/appointments/{appointment_id}/status", json={"status": new_status.value})


async def finance_counts(maker):
    return await count(maker, Transaction), await count(maker, BarberCommission)


async def other_barber_id(maker):
    user = await add_user(maker, "outro.barbeiro@teste.com", UserRole.BARBER)
    async with maker() as db:
        barber = Barber(user_id=user.id)
        db.add(barber)
        await db.commit()
        return barber.id


# ── Dono ─────────────────────────────────────────────────


async def test_barber_completes_own_started_appointment(client, sessionmaker, shop):
    appointment_id = await add_appointment(sessionmaker, shop, start=PAST)

    response = await change_as(client, shop["barber_user"], appointment_id, S.COMPLETED)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    assert await finance_counts(sessionmaker) == (1, 1)


async def test_barber_cannot_touch_other_barbers_appointment(client, sessionmaker, shop):
    appointment_id = await add_appointment(
        sessionmaker, shop, start=PAST, barber_id=await other_barber_id(sessionmaker)
    )

    response = await change_as(client, shop["barber_user"], appointment_id, S.COMPLETED)

    assert response.status_code == 404
    assert response.json()["detail"] == "Agendamento não encontrado."
    assert await status_in_db(sessionmaker, appointment_id) == S.CONFIRMED
    assert await finance_counts(sessionmaker) == (0, 0)


async def test_unknown_id_gets_404(client, sessionmaker, shop):
    response = await change_as(client, shop["barber_user"], uuid.uuid4(), S.COMPLETED)

    assert response.status_code == 404
    assert response.json()["detail"] == "Agendamento não encontrado."


async def test_admin_changes_any_barbers_appointment(client, sessionmaker, shop):
    appointment_id = await add_appointment(
        sessionmaker, shop, start=PAST, barber_id=await other_barber_id(sessionmaker)
    )
    admin = await add_user(sessionmaker, "admin@teste.com", UserRole.ADMIN)

    response = await change_as(client, admin, appointment_id, S.COMPLETED)

    assert response.status_code == 200, response.text
    assert await finance_counts(sessionmaker) == (1, 1)


async def test_client_role_is_forbidden(client, sessionmaker, shop):
    appointment_id = await add_appointment(sessionmaker, shop, start=PAST)

    response = await change_as(client, shop["client"], appointment_id, S.COMPLETED)

    assert response.status_code == 403
    assert await status_in_db(sessionmaker, appointment_id) == S.CONFIRMED


# ── Transições ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("current", "new", "start"),
    [
        (S.PENDING, S.CONFIRMED, FUTURE),
        (S.PENDING, S.CONFIRMED, PAST),
        (S.PENDING, S.CANCELLED, FUTURE),
        (S.CONFIRMED, S.CANCELLED, FUTURE),
        (S.CONFIRMED, S.COMPLETED, PAST),
        (S.CONFIRMED, S.NO_SHOW, PAST),
        (S.CONFIRMED, S.COMPLETED, NOW),
    ],
)
async def test_allowed_transitions(client, sessionmaker, shop, current, new, start):
    appointment_id = await add_appointment(sessionmaker, shop, start=start, status=current)

    response = await change_as(client, shop["barber_user"], appointment_id, new)

    assert response.status_code == 200, response.text
    assert await status_in_db(sessionmaker, appointment_id) == new


@pytest.mark.parametrize("new", list(S))
@pytest.mark.parametrize("current", FINAL)
async def test_final_statuses_never_change(client, sessionmaker, shop, current, new):
    appointment_id = await add_appointment(sessionmaker, shop, start=PAST, status=current)

    response = await change_as(client, shop["barber_user"], appointment_id, new)

    assert response.status_code == 400
    assert "inválida" in response.json()["detail"]
    assert await status_in_db(sessionmaker, appointment_id) == current
    assert await finance_counts(sessionmaker) == (0, 0)


@pytest.mark.parametrize(("current", "new"), [(S.PENDING, S.COMPLETED), (S.CONFIRMED, S.CONFIRMED), (S.PENDING, S.PENDING)])
async def test_other_invalid_transitions(client, sessionmaker, shop, current, new):
    appointment_id = await add_appointment(sessionmaker, shop, start=PAST, status=current)

    response = await change_as(client, shop["barber_user"], appointment_id, new)

    assert response.status_code == 400
    assert "inválida" in response.json()["detail"]
    assert await status_in_db(sessionmaker, appointment_id) == current


async def test_completed_cannot_go_back_so_charge_happens_once(client, sessionmaker, shop):
    appointment_id = await add_appointment(sessionmaker, shop, start=PAST)
    barber = shop["barber_user"]

    assert (await change_as(client, barber, appointment_id, S.COMPLETED)).status_code == 200
    assert (await change_as(client, barber, appointment_id, S.CONFIRMED)).status_code == 400
    assert (await change_as(client, barber, appointment_id, S.COMPLETED)).status_code == 400

    assert await status_in_db(sessionmaker, appointment_id) == S.COMPLETED
    assert await finance_counts(sessionmaker) == (1, 1)


# ── Horário ──────────────────────────────────────────────


@pytest.mark.parametrize("new", [S.COMPLETED, S.NO_SHOW])
async def test_cannot_finish_before_start(client, sessionmaker, shop, new):
    appointment_id = await add_appointment(sessionmaker, shop, start=FUTURE)

    response = await change_as(client, shop["barber_user"], appointment_id, new)

    assert response.status_code == 400
    assert "depois do início" in response.json()["detail"]
    assert await status_in_db(sessionmaker, appointment_id) == S.CONFIRMED
    assert await finance_counts(sessionmaker) == (0, 0)


@pytest.mark.parametrize("current", [S.PENDING, S.CONFIRMED])
async def test_cannot_cancel_after_start(client, sessionmaker, shop, current):
    appointment_id = await add_appointment(sessionmaker, shop, start=PAST, status=current)

    response = await change_as(client, shop["barber_user"], appointment_id, S.CANCELLED)

    assert response.status_code == 400
    assert "já começou" in response.json()["detail"]
    assert await status_in_db(sessionmaker, appointment_id) == current


# ── Cobrança única ───────────────────────────────────────


async def test_existing_transaction_is_not_duplicated(client, sessionmaker, shop):
    """Dado antigo: já existe cobrança para o agendamento, mas ele não está concluído."""
    appointment_id = await add_appointment(sessionmaker, shop, start=PAST)
    async with sessionmaker() as db:
        db.add(
            Transaction(
                type=TransactionType.APPOINTMENT,
                reference_id=appointment_id,
                amount=40,
                payment_method=PaymentMethod.PIX,
                user_id=shop["client"].id,
            )
        )
        await db.commit()

    response = await change_as(client, shop["barber_user"], appointment_id, S.COMPLETED)

    assert response.status_code == 200, response.text
    assert await finance_counts(sessionmaker) == (1, 0)
