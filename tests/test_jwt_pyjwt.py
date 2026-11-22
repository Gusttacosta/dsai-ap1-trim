"""
Testes da troca do python-jose pelo PyJWT (#42).

Spec: SPEC/2026-11-22-jwt-pyjwt.md

Os testes de `decode_token` não usam banco. O de ponta a ponta usa a API de verdade (`client`) e o
PostgreSQL de TEST_DATABASE_URL, e é pulado sem essa variável.
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest

from src.backend.config import settings
from src.backend.modules.auth import security
from src.backend.modules.auth.models import UserRole
from tests.agenda_fixtures import needs_db

REQUIREMENTS = Path(__file__).resolve().parent.parent / "requirements.txt"
CLAIMS = {"user_id": "5f0c8a4e-2b1d-4c3e-9a7f-1d2e3f4a5b6c", "email": "legado@teste.com", "role": "client"}

# Emitido pelo python-jose 3.4.0, antes da troca, com:
# jose.jwt.encode({**CLAIMS, "exp": 4102444800}, LEGACY_KEY, algorithm="HS256")
LEGACY_KEY = "chave-de-teste-do-token-legado"
LEGACY_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJ1c2VyX2lkIjoiNWYwYzhhNGUtMmIxZC00YzNlLTlhN2YtMWQyZTNmNGE1YjZjIiwiZW1haWwiOiJsZWdhZG9AdGVzdGUuY29tIiwicm9sZSI6ImNsaWVudCIsImV4cCI6NDEwMjQ0NDgwMH0"
    ".xTuB1ZM_7DoU4qshPYY9fxKcbLTi_5e2sfV4pyDYOig"
)


def header(token):
    segment = token.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))


def make_token(claims=CLAIMS, key=None, algorithm=None, expires_in=timedelta(minutes=5)):
    payload = {**claims, "exp": datetime.now(timezone.utc) + expires_in}
    return jwt.encode(payload, key or settings.secret_key, algorithm=algorithm or settings.algorithm)


# ── dependência ─────────────────────────────────────────


def test_requirements_fixa_o_pyjwt_e_nao_tem_python_jose():
    lines = [line.strip().lower() for line in REQUIREMENTS.read_text().splitlines()]

    assert "pyjwt==2.15.1" in lines
    assert not [line for line in lines if line.startswith("python-jose")]


def test_security_usa_o_jwt_do_pyjwt():
    assert security.jwt is jwt
    assert jwt.__name__ == "jwt"


# ── decode_token ────────────────────────────────────────


def test_token_do_create_access_token_e_aceito_com_as_mesmas_claims():
    token, expires_in = security.create_access_token(dict(CLAIMS), UserRole.CLIENT)

    payload = security.decode_token(token)

    assert {key: payload[key] for key in CLAIMS} == CLAIMS
    assert expires_in == 30 * 60
    assert payload["exp"] - datetime.now(timezone.utc).timestamp() == pytest.approx(30 * 60, abs=5)


def test_token_continua_com_cabecalho_hs256_jwt():
    token, _ = security.create_access_token(dict(CLAIMS), UserRole.ADMIN)

    assert header(token) == {"alg": "HS256", "typ": "JWT"}


def test_refresh_token_e_aceito_e_traz_o_tipo():
    token, _ = security.create_refresh_token(dict(CLAIMS), UserRole.CLIENT)

    assert security.decode_token(token)["type"] == "refresh"


def test_token_emitido_pelo_python_jose_continua_aceito(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", LEGACY_KEY)

    assert security.decode_token(LEGACY_TOKEN) == {**CLAIMS, "exp": 4102444800}


def test_token_assinado_com_outra_chave_e_recusado():
    token = make_token(key="outra-chave-qualquer-com-32-bytes-ou-mais")

    assert security.decode_token(token) is None


def test_token_com_assinatura_adulterada_e_recusado():
    token, _ = security.create_access_token(dict(CLAIMS), UserRole.CLIENT)
    head, body, signature = token.split(".")
    tampered = f"{head}.{body}.{signature[:-2]}{'AA' if signature[-2:] != 'AA' else 'BB'}"

    assert security.decode_token(tampered) is None


def test_token_vencido_e_recusado():
    assert security.decode_token(make_token(expires_in=timedelta(seconds=-1))) is None


def test_token_com_algoritmo_none_e_recusado():
    payload = {**CLAIMS, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    token = jwt.encode(payload, None, algorithm="none")

    assert header(token)["alg"] == "none"
    assert security.decode_token(token) is None


def test_token_com_outro_algoritmo_hmac_e_recusado():
    assert security.decode_token(make_token(algorithm="HS512")) is None


@pytest.mark.parametrize("token", ["", "isto-nao-e-um-jwt", "a.b.c"], ids=["vazio", "texto", "tres-partes"])
def test_token_malformado_e_recusado(token):
    assert security.decode_token(token) is None


# ── ponta a ponta ───────────────────────────────────────


@needs_db
@pytest.mark.asyncio
async def test_cadastro_login_e_me_funcionam_com_o_pyjwt(sessionmaker, client):
    email, password = "pyjwt@teste.com", "senhaForte123"
    register = await client.post(
        "/api/auth/register", json={"email": email, "password": password, "full_name": "Pessoa PyJWT"}
    )
    assert register.status_code == 201, register.text

    login = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me.status_code == 200, me.text
    assert me.json()["email"] == email
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["email"] == email
    assert header(token) == {"alg": "HS256", "typ": "JWT"}
