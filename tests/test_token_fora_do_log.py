"""
Testes do e-mail falso sem token no log fora de development (#30).

Spec: SPEC/2026-11-19-token-fora-do-log.md

Usam o PostgreSQL de TEST_DATABASE_URL. `settings.app_env` é fixado em cada teste, e todas as
mensagens de log (de qualquer logger) são conferidas.
"""

import logging

import pytest
from sqlalchemy import select

from src.backend.config import settings
from src.backend.modules.auth.models import EmailVerificationToken, PasswordResetToken, User
from tests.agenda_fixtures import needs_db

pytestmark = [pytest.mark.asyncio, needs_db]

EMAIL = "pessoa@teste.com"
PASSWORD = "senhaForte123"
NOT_DEVELOPMENT = ["production", "staging"]


@pytest.fixture
def app_env(monkeypatch):
    def _set(value):
        monkeypatch.setattr(settings, "app_env", value)

    return _set


@pytest.fixture
def logs(caplog):
    caplog.set_level(logging.INFO)
    caplog.clear()
    return caplog


def all_messages(caplog):
    return [r.getMessage() for r in caplog.records]


def mock_email_messages(caplog):
    return [m for m in all_messages(caplog) if m.startswith("[MOCK EMAIL]")]


async def register(client):
    response = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Pessoa"},
    )
    assert response.status_code == 201, response.text
    return response


async def forgot_password(client):
    response = await client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 200, response.text
    return response


async def stored(maker, model):
    async with maker() as db:
        return (await db.execute(select(model))).scalar_one()


async def user_id(maker):
    async with maker() as db:
        return (await db.execute(select(User.id).where(User.email == EMAIL))).scalar_one()


# ── fora de development ─────────────────────────────────


@pytest.mark.parametrize("env", NOT_DEVELOPMENT)
async def test_cadastro_nao_registra_token_nem_email(env, app_env, sessionmaker, client, logs):
    app_env(env)

    await register(client)

    token = (await stored(sessionmaker, EmailVerificationToken)).token
    messages = all_messages(logs)
    assert not any(token in m for m in messages)
    assert not any(EMAIL in m for m in messages)
    (message,) = mock_email_messages(logs)
    assert message == (
        f"[MOCK EMAIL] Verificacao de email gerada para o usuario {await user_id(sessionmaker)}; "
        "envio de email nao configurado (token omitido fora de development)."
    )


@pytest.mark.parametrize("env", NOT_DEVELOPMENT)
async def test_redefinicao_nao_registra_token_nem_email(env, app_env, sessionmaker, client, logs):
    app_env(env)
    await register(client)
    logs.clear()

    await forgot_password(client)

    token = (await stored(sessionmaker, PasswordResetToken)).token
    messages = all_messages(logs)
    assert not any(token in m for m in messages)
    assert not any(EMAIL in m for m in messages)
    (message,) = mock_email_messages(logs)
    assert message == (
        f"[MOCK EMAIL] Redefinicao de senha gerada para o usuario {await user_id(sessionmaker)}; "
        "envio de email nao configurado (token omitido fora de development)."
    )


async def test_token_gerado_em_producao_continua_valido(app_env, sessionmaker, client):
    app_env("production")
    await register(client)
    await forgot_password(client)
    token = (await stored(sessionmaker, PasswordResetToken)).token

    response = await client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": "outraSenha456"}
    )

    assert response.status_code == 200, response.text
    login = await client.post(
        "/api/auth/login", json={"email": EMAIL, "password": "outraSenha456"}
    )
    assert login.status_code == 200, login.text


async def test_email_desconhecido_em_producao_nao_registra_nada(app_env, sessionmaker, client, logs):
    app_env("production")

    response = await client.post("/api/auth/forgot-password", json={"email": "ninguem@teste.com"})

    assert response.status_code == 200
    assert mock_email_messages(logs) == []


# ── development ─────────────────────────────────────────


async def test_cadastro_em_development_mostra_email_e_token(app_env, sessionmaker, client, logs):
    app_env("development")

    await register(client)

    token = (await stored(sessionmaker, EmailVerificationToken)).token
    assert mock_email_messages(logs) == [
        f"[MOCK EMAIL] Para verificar o email de {EMAIL}, use o token: {token}"
    ]


async def test_redefinicao_em_development_mostra_email_e_link(app_env, sessionmaker, client, logs):
    app_env("development")
    await register(client)
    logs.clear()

    await forgot_password(client)

    token = (await stored(sessionmaker, PasswordResetToken)).token
    assert mock_email_messages(logs) == [
        f"[MOCK EMAIL] Link de reset para {EMAIL}: /reset-password?token={token}"
    ]
