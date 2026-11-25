"""
Aplica as migrações do Alembic antes de a API subir (#6, SPEC/2026-11-25-alembic-migracoes.md).

- Banco vazio: `upgrade head` cria tudo a partir da 0001.
- Banco antigo, com as tabelas do `create_all` e sem `alembic_version` (é o caso da produção):
  `stamp 0001` registra que o esquema inicial já existe, e o `upgrade head` aplica só o que vem
  depois.
- Banco já versionado: `upgrade head`.

Uso: python scripts/migrate.py   (o Procfile e o render.yaml rodam isto antes do uvicorn)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import Connection, create_engine, inspect  # noqa: E402

BASELINE = "0001"


def alembic_config(connection: Connection | None = None) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    if connection is not None:
        # O env.py usa esta conexão em vez de abrir outra (os testes usam um schema próprio).
        config.attributes["connection"] = connection
    return config


def needs_stamp(connection: Connection) -> bool:
    tables = set(inspect(connection).get_table_names())
    return "alembic_version" not in tables and "users" in tables


def migrate(connection: Connection) -> str:
    """Leva o banco da conexão até a última revisão. Devolve o que foi feito."""
    config = alembic_config(connection)
    action = "upgrade"
    if needs_stamp(connection):
        command.stamp(config, BASELINE)
        action = "stamp+upgrade"
    command.upgrade(config, "head")
    return action


def main() -> None:
    from src.backend.config import settings

    engine = create_engine(settings.database_url_sync)
    with engine.begin() as connection:
        action = migrate(connection)
    engine.dispose()
    print(f"Migrações aplicadas ({action}).")


if __name__ == "__main__":
    main()
