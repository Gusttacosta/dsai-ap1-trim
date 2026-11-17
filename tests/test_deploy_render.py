"""
Testes do deploy no Render.

Spec: SPEC/2026-11-16-deploy-render.md
"""

import pytest

from src.backend.config import Settings


def make_settings(monkeypatch, **overrides) -> Settings:
    """Settings sem .env e sem as variáveis do ambiente que os testes conferem."""
    for var in ("DATABASE_URL", "CORS_ORIGINS", "RENDER_GIT_COMMIT"):
        monkeypatch.delenv(var, raising=False)
    return Settings(_env_file=None, **overrides)


# ── DATABASE_URL do Render ───────────────────────────────


@pytest.mark.parametrize(
    "render_url",
    ["postgresql://trim:senha@host:5432/trim", "postgres://trim:senha@host:5432/trim"],
)
def test_render_database_url_is_converted_for_asyncpg_and_psycopg2(monkeypatch, render_url):
    s = make_settings(monkeypatch, database_url=render_url)

    assert s.database_url_async == "postgresql+asyncpg://trim:senha@host:5432/trim"
    assert s.database_url_sync == "postgresql+psycopg2://trim:senha@host:5432/trim"
