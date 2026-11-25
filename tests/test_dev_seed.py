"""
Testes das rotas /api/dev/seed e /api/dev/update_dates.

Spec: SPEC/2026-11-16-seed-seguro.md

Os testes de banco precisam de um PostgreSQL em TEST_DATABASE_URL e usam um
schema novo e descartável a cada teste. Sem essa variável, são pulados.
"""

import logging
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.config import settings
from src.backend.database import Base, get_db
from src.backend.main import app
from src.backend.modules import dev_router
from src.backend.modules.auth.models import User
from src.backend.modules.auth.security import verify_password
from src.backend.modules.subscriptions import models as subscription_models
from src.backend.modules.subscriptions.models import SubscriptionPlan

SECRET = "segredo-de-teste"
ADMIN_PASSWORD = "senha-admin-de-teste"
DEMO_PASSWORD = "senha-demo-de-teste"
DEMO_EMAILS = ["carlos@trim.com", "cliente@trim.com"]
ROUTES = ["/api/dev/seed", "/api/dev/update_dates"]
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture(autouse=True)
def seed_settings(monkeypatch):
    monkeypatch.setattr(settings, "seed_secret", SECRET)
    monkeypatch.setattr(settings, "seed_admin_password", ADMIN_PASSWORD)
    monkeypatch.setattr(settings, "seed_demo_password", DEMO_PASSWORD)
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Proteção das rotas ───────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("value", ["", None])
async def test_route_is_404_without_seed_secret(client, monkeypatch, route, value):
    monkeypatch.setattr(settings, "seed_secret", value or "")

    response = await client.post(route, headers={"X-Seed-Secret": SECRET})

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("headers", [{}, {"X-Seed-Secret": "errado"}, {"X-Seed-Secret": SECRET + "x"}])
async def test_route_refuses_wrong_secret(client, route, headers):
    response = await client.post(route, headers=headers)

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
async def test_old_query_string_secret_is_refused(client, route):
    response = await client.post(f"{route}?secret={SECRET}")

    assert response.status_code == 403


def test_secret_is_compared_with_compare_digest(monkeypatch):
    calls = []

    def fake_compare_digest(a, b):
        calls.append((a, b))
        return True

    monkeypatch.setattr(dev_router.secrets, "compare_digest", fake_compare_digest)

    dev_router.require_seed_secret(x_seed_secret="qualquer")

    assert calls == [(b"qualquer", SECRET.encode())]


# ── Erros sem traceback ──────────────────────────────────


class BrokenSession:
    """Sessão que falha em qualquer consulta, com um detalhe interno na mensagem."""

    def __init__(self):
        self.rolled_back = False

    async def execute(self, *args, **kwargs):
        raise RuntimeError("detalhe-interno-do-banco")

    def add(self, *args, **kwargs):
        raise RuntimeError("detalhe-interno-do-banco")

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
async def test_error_returns_500_without_traceback(client, caplog, route):
    session = BrokenSession()

    async def broken_db():
        yield session

    app.dependency_overrides[get_db] = broken_db

    with caplog.at_level(logging.ERROR, logger=dev_router.logger.name):
        response = await client.post(route, headers={"X-Seed-Secret": SECRET})

    assert response.status_code == 500
    assert response.json() == {"detail": dev_router.GENERIC_ERROR}
    assert "Traceback" not in response.text
    assert "detalhe-interno-do-banco" not in response.text
    assert session.rolled_back
    assert "detalhe-interno-do-banco" in caplog.text


# ── Seed num banco novo (PostgreSQL) ─────────────────────


@pytest_asyncio.fixture
async def db_sessionmaker():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL não definida")

    schema = f"seed_test_{uuid.uuid4().hex[:12]}"
    admin_engine = create_async_engine(TEST_DATABASE_URL)
    async with admin_engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def test_db():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    try:
        yield sessionmaker
    finally:
        await engine.dispose()
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


async def demo_hashes(sessionmaker):
    async with sessionmaker() as session:
        users = (await session.execute(select(User).where(User.email.in_(DEMO_EMAILS)))).scalars().all()
    return {u.email: u.hashed_password for u in users}


async def count(sessionmaker, model):
    async with sessionmaker() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


@pytest.mark.asyncio
async def test_seed_populates_new_database(client, db_sessionmaker):
    response = await client.post("/api/dev/seed", headers={"X-Seed-Secret": SECRET})

    assert response.status_code == 200, response.text
    async with db_sessionmaker() as session:
        plans = (await session.execute(select(SubscriptionPlan))).scalars().all()
        admin = (
            await session.execute(select(User).where(User.email == "admin@trim.com"))
        ).scalar_one()

    by_name = {p.name: (float(p.monthly_price), p.included_cuts, p.included_shaves) for p in plans}
    assert by_name == {
        "Básico": (80.0, 2, 0),
        "Executivo": (150.0, None, 2),  # cortes ilimitados (#16)
        "Barba & Cabelo": (120.0, 2, 2),
    }
    assert verify_password(ADMIN_PASSWORD, admin.hashed_password)
    assert await count(db_sessionmaker, User) == 3
    hashes = await demo_hashes(db_sessionmaker)
    assert sorted(hashes) == DEMO_EMAILS
    assert all(verify_password(DEMO_PASSWORD, h) for h in hashes.values())


@pytest.mark.asyncio
async def test_seed_without_demo_password_blocks_demo_login(client, db_sessionmaker, monkeypatch):
    monkeypatch.setattr(settings, "seed_demo_password", "")

    response = await client.post("/api/dev/seed", headers={"X-Seed-Secret": SECRET})

    assert response.status_code == 200, response.text
    hashes = await demo_hashes(db_sessionmaker)
    assert sorted(hashes) == DEMO_EMAILS
    for h in hashes.values():
        assert not verify_password("", h)
        assert not verify_password(DEMO_PASSWORD, h)


@pytest.mark.asyncio
async def test_seed_twice_does_not_duplicate(client, db_sessionmaker):
    headers = {"X-Seed-Secret": SECRET}
    assert (await client.post("/api/dev/seed", headers=headers)).status_code == 200

    response = await client.post("/api/dev/seed", headers=headers)

    assert response.status_code == 200, response.text
    assert await count(db_sessionmaker, User) == 3
    assert await count(db_sessionmaker, SubscriptionPlan) == 3


@pytest.mark.asyncio
async def test_seed_without_admin_password_skips_admin(client, db_sessionmaker, monkeypatch):
    monkeypatch.setattr(settings, "seed_admin_password", "")

    response = await client.post("/api/dev/seed", headers={"X-Seed-Secret": SECRET})

    assert response.status_code == 200, response.text
    async with db_sessionmaker() as session:
        emails = set((await session.execute(select(User.email))).scalars().all())
    assert emails == {"carlos@trim.com", "cliente@trim.com"}
    assert await count(db_sessionmaker, SubscriptionPlan) == 3


@pytest.mark.asyncio
async def test_seed_failure_writes_nothing(client, db_sessionmaker, monkeypatch):
    # Os planos são a última etapa: se ela falha, as anteriores também não podem ficar gravadas.
    def broken_plan(*args, **kwargs):
        raise RuntimeError("falha nos planos")

    monkeypatch.setattr(subscription_models, "SubscriptionPlan", broken_plan)

    response = await client.post("/api/dev/seed", headers={"X-Seed-Secret": SECRET})

    assert response.status_code == 500
    assert await count(db_sessionmaker, User) == 0
