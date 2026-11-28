"""
Fixtures e funções de apoio compartilhadas pelos testes de agendamento.

Os testes de banco precisam de um PostgreSQL em TEST_DATABASE_URL e usam um schema novo e
descartável a cada teste. "Agora" é fixado substituindo `utc_now` no módulo do serviço.
"""

import os
import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.database import Base, get_db
from src.backend.main import app
from src.backend.modules.appointments import service as appointment_service
from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber, WorkSchedule
from src.backend.modules.services.models import BarberServiceAssociation, Service

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
BRT = ZoneInfo("America/Sao_Paulo")
needs_db = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL não definida")


def brt(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=BRT)


@pytest.fixture
def set_now(monkeypatch):
    def _set(moment: datetime):
        monkeypatch.setattr(
            appointment_service, "utc_now", lambda: moment.astimezone(timezone.utc), raising=False
        )

    return _set


@pytest_asyncio.fixture
async def sessionmaker():
    schema = f"agenda_test_{uuid.uuid4().hex[:12]}"
    admin_engine = create_async_engine(TEST_DATABASE_URL)
    async with admin_engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def test_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    try:
        yield maker
    finally:
        await engine.dispose()
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def create_shop(maker, *, days=range(7), start="09:00", end="18:00", lunch=None):
    """Cria um cliente, um barbeiro com expediente nos `days` (0 = domingo) e um corte de 30 min."""
    async with maker() as db:
        client_user = User(
            email="cliente@teste.com", hashed_password="x", full_name="Cliente", role=UserRole.CLIENT
        )
        barber_user = User(
            email="barbeiro@teste.com", hashed_password="x", full_name="Barbeiro", role=UserRole.BARBER
        )
        db.add_all([client_user, barber_user])
        await db.flush()

        barber = Barber(user_id=barber_user.id)
        service = Service(name="Corte", price=40, duration_minutes=30)
        db.add_all([barber, service])
        await db.flush()

        db.add(BarberServiceAssociation(barber_id=barber.id, service_id=service.id))
        for day in range(7):
            db.add(
                WorkSchedule(
                    barber_id=barber.id,
                    day_of_week=day,
                    start_time=time.fromisoformat(start),
                    end_time=time.fromisoformat(end),
                    break_start=time.fromisoformat(lunch[0]) if lunch else None,
                    break_end=time.fromisoformat(lunch[1]) if lunch else None,
                    is_working=day in days,
                )
            )
        await db.commit()
        return {
            "client": client_user,
            "barber_user": barber_user,
            "barber_id": barber.id,
            "service_id": service.id,
        }


async def count(maker, model):
    async with maker() as db:
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()


async def add_user(maker, email, role=UserRole.CLIENT):
    async with maker() as db:
        user = User(email=email, hashed_password="x", full_name=email.split("@")[0], role=role)
        db.add(user)
        await db.commit()
        return user


async def add_appointment(maker, shop, *, start, status=AppointmentStatus.CONFIRMED, barber_id=None):
    """Cria um agendamento de 30 min do cliente da barbearia de teste."""
    async with maker() as db:
        appointment = Appointment(
            client_id=shop["client"].id,
            barber_id=barber_id or shop["barber_id"],
            start_datetime=start,
            end_datetime=start + timedelta(minutes=30),
            status=status,
            total_price=40,
        )
        db.add(appointment)
        await db.commit()
        return appointment.id


async def status_in_db(maker, appointment_id):
    async with maker() as db:
        stmt = select(Appointment.status).where(Appointment.id == appointment_id)
        return (await db.execute(stmt)).scalar_one()
