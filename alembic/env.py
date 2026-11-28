"""
Alembic Environment Configuration for Trim.

Configura o Alembic para usar os models do SQLAlchemy e
a URL do banco de dados das settings.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.backend.config import settings
from src.backend.database import Base

# ── Alembic Config ───────────────────────────────────────
config = context.config

# Override da URL do banco com a do .env (sync para migrations)
# "%" é interpolação para o configparser: uma senha com "%" derrubaria a migração no deploy.
config.set_main_option("sqlalchemy.url", settings.database_url_sync.replace("%", "%%"))

# Logging do alembic.ini só no CLI. Chamado por scripts/migrate.py ou pelos testes (com a conexão em
# config.attributes), o fileConfig desligaria os loggers da aplicação e poria a raiz em WARN (#6).
if config.config_file_name is not None and "connection" not in config.attributes:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# ── Target metadata (todos os models) ───────────────────
# Importar todos os models aqui para que o Alembic os detecte
from src.backend.modules.auth.models import *  # noqa
from src.backend.modules.barbers.models import *  # noqa
from src.backend.modules.services.models import *  # noqa
from src.backend.modules.appointments.models import *  # noqa
from src.backend.modules.products.models import *  # noqa
from src.backend.modules.subscriptions.models import *  # noqa
from src.backend.modules.finance.models import *  # noqa
from src.backend.modules.expenses.models import *  # noqa
from src.backend.modules.walkin.models import *  # noqa
from src.backend.modules.gallery.models import *  # noqa
from src.backend.modules.loyalty.models import *  # noqa
from src.backend.modules.notifications.models import *  # noqa
# (adicionar conforme os models forem criados)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # scripts/migrate.py (e os testes) podem passar a própria conexão (#6).
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

    ini_section = config.get_section(config.config_ini_section, {})
    ini_section["sqlalchemy.url"] = settings.database_url_sync
    
    connectable = engine_from_config(
        ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
