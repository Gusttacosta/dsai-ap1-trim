"""
Migrações do Alembic (#6, SPEC/2026-11-25-alembic-migracoes.md).

Cada teste usa um schema novo no PostgreSQL de TEST_DATABASE_URL, pela conexão síncrona
(psycopg2), que é a que o Alembic usa.
"""

import os
import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from scripts.migrate import alembic_config, migrate
from src.backend.database import Base
from tests.agenda_fixtures import needs_db

pytestmark = needs_db

CHECK = "ck_loyalty_wallets_balance_non_negative"


def sync_url() -> str:
    url = os.environ["TEST_DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)


@pytest.fixture
def connection():
    schema = f"mig_{uuid.uuid4().hex[:12]}"
    admin = create_engine(sync_url())
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(sync_url(), connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.connect() as conn:
            yield conn
            conn.rollback()
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def head() -> str:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def current(conn) -> str | None:
    return MigrationContext.configure(conn).get_current_revision()


def has_check(conn) -> bool:
    return conn.execute(text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": CHECK}).first() is not None


def test_there_is_a_single_head():
    assert ScriptDirectory.from_config(alembic_config()).get_heads() == [head()]


def test_empty_database_is_created_by_the_migrations(connection):
    assert migrate(connection) == "upgrade"
    assert current(connection) == head()
    tables = set(inspect(connection).get_table_names()) - {"alembic_version"}
    assert tables == set(Base.metadata.tables)
    assert has_check(connection)


def test_models_and_migrations_do_not_diverge(connection):
    """Falha quando um modelo muda sem migração nova."""
    migrate(connection)
    diff = compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata)
    assert diff == []


def test_legacy_database_is_stamped_and_upgraded(connection):
    """O banco de produção: tabelas do create_all, sem alembic_version e sem a trava de saldo."""
    Base.metadata.create_all(connection)
    connection.execute(text(f"ALTER TABLE loyalty_wallets DROP CONSTRAINT {CHECK}"))
    connection.execute(text(
        "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, email_verified) "
        "VALUES (gen_random_uuid(), 'antigo@teste.com', 'x', 'Antigo', 'CLIENT', true, false)"
    ))

    connection.execute(text(
        "INSERT INTO subscription_plans (id, name, monthly_price, included_cuts, included_shaves, "
        "discount_percentage, is_active) VALUES (gen_random_uuid(), 'Executivo', 150, 30, 2, 0, true)"
    ))

    assert migrate(connection) == "stamp+upgrade"

    assert current(connection) == head()
    assert has_check(connection)
    # O Executivo do seed antigo (30 cortes, #16) passa a ilimitado.
    cuts = connection.execute(text("SELECT included_cuts FROM subscription_plans WHERE name = 'Executivo'")).scalar_one()
    assert cuts is None
    # Os dados de antes continuam lá.
    assert connection.execute(text("SELECT count(*) FROM users")).scalar_one() == 1


def test_running_again_changes_nothing(connection):
    migrate(connection)
    assert migrate(connection) == "upgrade"
    assert current(connection) == head()


def test_downgrade_to_base_removes_everything(connection):
    from alembic import command

    migrate(connection)
    command.downgrade(alembic_config(connection), "base")
    assert set(inspect(connection).get_table_names()) == {"alembic_version"}
    enums = connection.execute(text(
        "SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
        "WHERE n.nspname = current_schema() AND t.typtype = 'e'"
    )).scalar_one()
    assert enums == 0
