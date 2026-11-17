"""
Testes do deploy no Render.

Spec: SPEC/2026-11-16-deploy-render.md
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.config import Settings, settings
from src.backend.main import app


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


# ── CORS padrão ──────────────────────────────────────────


def test_default_cors_origins_are_local_only(monkeypatch):
    origins = make_settings(monkeypatch).cors_origins_list

    assert origins == ["http://localhost:5173", "http://localhost:3000"]
    assert not any("railway" in origin for origin in origins)


# ── /health com o commit no ar ───────────────────────────


@pytest.mark.asyncio
async def test_health_returns_render_git_commit(monkeypatch):
    monkeypatch.setattr(settings, "render_git_commit", "0123abcd")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "app": "Trim",
        "version": "0.1.0",
        "commit": "0123abcd",
    }


def test_render_git_commit_comes_from_env(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "0123abcd")

    assert Settings(_env_file=None).render_git_commit == "0123abcd"


def test_render_git_commit_defaults_to_local(monkeypatch):
    assert make_settings(monkeypatch).render_git_commit == "local"
