"""
Testes do refresh do access token e do logout que revoga a sessão (#35).

Spec: SPEC/2026-11-22-auth-refresh-logout.md

O cookie é gravado com `Secure`, e o cliente de teste usa http://test, então o jar do httpx não o
devolve sozinho. Os testes mandam o cookie no cabeçalho `Cookie`, como o navegador faria.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, update

from src.backend.config import settings
from src.backend.modules.auth.models import RefreshToken, User, UserRole
from src.backend.modules.auth.service import AuthService
from tests.agenda_fixtures import needs_db
from tests.test_auth_integracao import (
    NEW_PASSWORD,
    PASSWORD,
    add_user,
    decode,
    login,
    make_token,
    refresh_cookie_header,
    refresh_token_from,
)

pytestmark = [pytest.mark.asyncio, needs_db]

EMAIL = "cliente@teste.com"
CLIENT_REFRESH_SECONDS = 7 * 24 * 60 * 60
STAFF_REFRESH_SECONDS = 30 * 24 * 60 * 60
REFRESH_ERROR = "Sessão inválida ou expirada. Entre novamente."


# ── apoio ───────────────────────────────────────────────


def with_cookie(token, **headers):
    return {"Cookie": f"refresh_token={token}", **headers}


async def refresh(client, token=None, **headers):
    if token is not None:
        headers = with_cookie(token, **headers)
    return await client.post("/api/auth/refresh", headers=headers)


async def logout(client, token=None, **headers):
    if token is not None:
        headers = with_cookie(token, **headers)
    return await client.post("/api/auth/logout", headers=headers)


async def session_token(maker, client, email=EMAIL, role=UserRole.CLIENT):
    """Cria o usuário, faz login e devolve o refresh token do cookie."""
    await add_user(maker, email, role)
    response = await login(client, email)
    assert response.status_code == 200, response.text
    return refresh_token_from(response)


async def rows(maker, **filters):
    async with maker() as db:
        stmt = select(RefreshToken).filter_by(**filters).order_by(RefreshToken.created_at)
        return (await db.execute(stmt)).scalars().all()


async def row_of(maker, token):
    async with maker() as db:
        return await db.get(RefreshToken, uuid.UUID(decode(token)["jti"]))


async def age_revocation(maker, token, seconds):
    """Recua o `revoked_at` do token, como se ele tivesse sido trocado há `seconds` segundos."""
    async with maker() as db:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == uuid.UUID(decode(token)["jti"]))
            .values(revoked_at=datetime.now(timezone.utc) - timedelta(seconds=seconds))
        )
        await db.commit()


def cookie_attributes(response):
    parts = [p.strip() for p in refresh_cookie_header(response).split(";")[1:]]
    return {p.split("=", 1)[0].lower(): (p.split("=", 1)[1] if "=" in p else True) for p in parts}


# ── emissão no login e no cadastro ──────────────────────


async def test_login_grava_a_sessao_e_o_jti_do_refresh(sessionmaker, client):
    token = await session_token(sessionmaker, client)

    saved = await rows(sessionmaker)
    assert len(saved) == 1
    assert decode(token)["jti"] == str(saved[0].id)
    assert saved[0].revoked_at is None
    async with sessionmaker() as db:
        assert (await db.get(User, saved[0].user_id)).email == EMAIL


async def test_cadastro_tambem_abre_uma_sessao(sessionmaker, client):
    response = await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Cliente"},
    )

    assert response.status_code == 201, response.text
    saved = await rows(sessionmaker)
    assert [str(r.id) for r in saved] == [decode(refresh_token_from(response))["jti"]]


async def test_cada_login_abre_uma_familia_nova(sessionmaker, client):
    await add_user(sessionmaker, EMAIL)
    await login(client, EMAIL)
    await login(client, EMAIL)

    saved = await rows(sessionmaker)
    assert len(saved) == 2
    assert saved[0].family_id != saved[1].family_id


@pytest.mark.parametrize(
    ("role", "max_age"),
    [
        (UserRole.CLIENT, CLIENT_REFRESH_SECONDS),
        (UserRole.BARBER, STAFF_REFRESH_SECONDS),
        (UserRole.ADMIN, STAFF_REFRESH_SECONDS),
    ],
)
async def test_cookie_dura_o_mesmo_que_o_refresh_token(sessionmaker, client, role, max_age):
    await add_user(sessionmaker, EMAIL, role)
    response = await login(client, EMAIL)

    attrs = cookie_attributes(response)
    assert int(attrs["max-age"]) == max_age
    assert attrs["path"] == "/api/auth"
    assert attrs["httponly"] is True
    assert attrs["secure"] is True
    saved = (await rows(sessionmaker))[0]
    lifetime = saved.expires_at - datetime.now(timezone.utc)
    assert abs(lifetime.total_seconds() - max_age) < 60


async def test_samesite_do_cookie_vem_da_configuracao(sessionmaker, client, monkeypatch):
    monkeypatch.setattr(settings, "refresh_cookie_samesite", "none")
    await add_user(sessionmaker, EMAIL)

    response = await login(client, EMAIL)

    assert cookie_attributes(response)["samesite"].lower() == "none"


# ── refresh ─────────────────────────────────────────────


async def test_refresh_devolve_tokens_novos_e_gira_o_cookie(sessionmaker, client):
    old = await session_token(sessionmaker, client)

    response = await refresh(client, old)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60
    assert body["user"]["email"] == EMAIL
    assert "hashed_password" not in body["user"]
    new = refresh_token_from(response)
    assert new != old
    assert int(cookie_attributes(response)["max-age"]) == CLIENT_REFRESH_SECONDS

    old_row, new_row = await row_of(sessionmaker, old), await row_of(sessionmaker, new)
    assert old_row.revoked_at is not None
    assert new_row.revoked_at is None
    assert new_row.family_id == old_row.family_id


async def test_access_token_do_refresh_abre_rotas_protegidas(sessionmaker, client):
    token = await session_token(sessionmaker, client)

    access = (await refresh(client, token)).json()["access_token"]
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})

    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


async def test_refresh_em_sequencia_mantem_a_familia(sessionmaker, client):
    token = await session_token(sessionmaker, client)
    for _ in range(3):
        response = await refresh(client, token)
        assert response.status_code == 200, response.text
        token = refresh_token_from(response)

    saved = await rows(sessionmaker)
    assert len(saved) == 4
    assert len({r.family_id for r in saved}) == 1
    assert [r.revoked_at is None for r in saved] == [False, False, False, True]


async def test_refresh_usa_o_perfil_atual_do_banco(sessionmaker, client):
    token = await session_token(sessionmaker, client)
    async with sessionmaker() as db:
        await db.execute(update(User).where(User.email == EMAIL).values(role=UserRole.BARBER))
        await db.commit()

    response = await refresh(client, token)

    assert response.status_code == 200, response.text
    assert response.json()["expires_in"] == 12 * 60 * 60
    assert response.json()["user"]["role"] == "barber"
    assert decode(response.json()["access_token"])["role"] == "barber"
    assert int(cookie_attributes(response)["max-age"]) == STAFF_REFRESH_SECONDS


async def test_refresh_sem_cookie_responde_401(sessionmaker, client):
    response = await refresh(client)

    assert response.status_code == 401
    assert response.json()["detail"] == REFRESH_ERROR


@pytest.mark.parametrize(
    "kind",
    ["malformado", "outra_chave", "vencido", "access_token", "sem_jti", "jti_invalido", "jti_desconhecido"],
)
async def test_refresh_recusa_tokens_que_nao_sao_uma_sessao_valida(sessionmaker, client, kind):
    user = await add_user(sessionmaker, EMAIL)
    claims = {"user_id": str(user.id), "email": EMAIL, "role": "client", "type": "refresh"}
    valid_jti = decode(refresh_token_from(await login(client, EMAIL)))["jti"]
    tokens = {
        "malformado": "nao-e-um-jwt",
        "outra_chave": make_token({**claims, "jti": valid_jti}, key="outra-chave-qualquer"),
        "vencido": make_token({**claims, "jti": valid_jti}, expires_in=timedelta(seconds=-5)),
        "access_token": make_token({k: v for k, v in claims.items() if k != "type"} | {"jti": valid_jti}),
        "sem_jti": make_token(claims),
        "jti_invalido": make_token({**claims, "jti": "abc"}),
        "jti_desconhecido": make_token({**claims, "jti": str(uuid.uuid4())}),
    }

    response = await refresh(client, tokens[kind])

    assert response.status_code == 401, kind
    assert (await rows(sessionmaker))[0].revoked_at is None


async def test_refresh_com_a_sessao_vencida_no_banco_responde_401(sessionmaker, client):
    token = await session_token(sessionmaker, client)
    async with sessionmaker() as db:
        await db.execute(
            update(RefreshToken).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        )
        await db.commit()

    assert (await refresh(client, token)).status_code == 401


async def test_reuso_de_token_trocado_revoga_a_familia(sessionmaker, client):
    old = await session_token(sessionmaker, client)
    new = refresh_token_from(await refresh(client, old))
    await age_revocation(sessionmaker, old, 11)

    response = await refresh(client, old)

    assert response.status_code == 401
    assert (await row_of(sessionmaker, new)).revoked_at is not None
    assert (await refresh(client, new)).status_code == 401


async def test_reuso_dentro_da_janela_de_corrida_nao_revoga_a_familia(sessionmaker, client):
    old = await session_token(sessionmaker, client)
    new = refresh_token_from(await refresh(client, old))

    response = await refresh(client, old)

    assert response.status_code == 401
    assert (await row_of(sessionmaker, new)).revoked_at is None
    assert (await refresh(client, new)).status_code == 200


async def test_reuso_nao_afeta_outras_sessoes_do_usuario(sessionmaker, client):
    old = await session_token(sessionmaker, client)
    other = refresh_token_from(await login(client, EMAIL))
    await refresh(client, old)
    await age_revocation(sessionmaker, old, 60)

    assert (await refresh(client, old)).status_code == 401
    assert (await refresh(client, other)).status_code == 200


async def test_usuario_desativado_nao_renova(sessionmaker, client):
    token = await session_token(sessionmaker, client)
    async with sessionmaker() as db:
        await db.execute(update(User).where(User.email == EMAIL).values(is_active=False))
        await db.commit()

    assert (await refresh(client, token)).status_code == 401


async def test_usuario_apagado_nao_renova(sessionmaker, client):
    token = await session_token(sessionmaker, client)
    async with sessionmaker() as db:
        await db.execute(delete(User).where(User.email == EMAIL))
        await db.commit()

    assert (await refresh(client, token)).status_code == 401
    assert await rows(sessionmaker) == []


# ── origem ──────────────────────────────────────────────


@pytest.mark.parametrize("route", [refresh, logout])
async def test_origem_fora_do_cors_recebe_403(sessionmaker, client, route):
    token = await session_token(sessionmaker, client)

    response = await route(client, token, Origin="https://site-malicioso.example")

    assert response.status_code == 403
    assert response.json()["detail"] == "Origem não permitida."
    assert (await row_of(sessionmaker, token)).revoked_at is None


async def test_origem_permitida_passa(sessionmaker, client):
    token = await session_token(sessionmaker, client)

    response = await refresh(client, token, Origin=settings.cors_origins_list[0])

    assert response.status_code == 200, response.text


# ── logout ──────────────────────────────────────────────


async def test_logout_revoga_a_sessao_e_o_refresh_seguinte_falha(sessionmaker, client):
    old = await session_token(sessionmaker, client)
    current = refresh_token_from(await refresh(client, old))

    response = await logout(client, current)

    assert response.status_code == 200
    assert all(r.revoked_at is not None for r in await rows(sessionmaker))
    assert (await refresh(client, current)).status_code == 401


async def test_logout_nao_encerra_outras_sessoes(sessionmaker, client):
    phone = await session_token(sessionmaker, client)
    laptop = refresh_token_from(await login(client, EMAIL))

    await logout(client, phone)

    assert (await refresh(client, phone)).status_code == 401
    assert (await refresh(client, laptop)).status_code == 200


@pytest.mark.parametrize("token", [None, "nao-e-um-jwt"])
async def test_logout_sem_sessao_valida_responde_200(sessionmaker, client, token):
    response = await logout(client, token)

    assert response.status_code == 200
    assert response.json()["message"] == "Logout efetuado com sucesso."


async def test_logout_apaga_o_cookie_no_mesmo_caminho(sessionmaker, client):
    token = await session_token(sessionmaker, client)

    attrs = cookie_attributes(await logout(client, token))

    assert attrs["path"] == "/api/auth"
    assert attrs["max-age"] == "0"


# ── redefinição de senha ────────────────────────────────


async def test_redefinir_a_senha_encerra_todas_as_sessoes(sessionmaker, client):
    first = await session_token(sessionmaker, client)
    second = refresh_token_from(await login(client, EMAIL))
    other_user = await session_token(sessionmaker, client, "outra@teste.com")
    async with sessionmaker() as db:
        reset = await AuthService(db).create_password_reset_token(EMAIL)

    response = await client.post(
        "/api/auth/reset-password", json={"token": reset, "new_password": NEW_PASSWORD}
    )

    assert response.status_code == 200, response.text
    assert (await refresh(client, first)).status_code == 401
    assert (await refresh(client, second)).status_code == 401
    assert (await refresh(client, other_user)).status_code == 200
