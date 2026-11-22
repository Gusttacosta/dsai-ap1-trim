"""
Testes de integração do módulo de autenticação (#3).

Spec: SPEC/2026-11-21-testes-integracao-auth.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Substituem o tests/test_auth.py gerado, que não importava a aplicação.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from fastapi import HTTPException
import jwt
from sqlalchemy import func, select, update

from src.backend.config import settings
from src.backend.modules.auth import security
from src.backend.modules.auth.dependencies import get_current_admin, get_current_barber_or_admin
from src.backend.modules.auth.models import (
    EmailVerificationToken,
    PasswordResetToken,
    User,
    UserRole,
)
from tests.agenda_fixtures import needs_db

pytestmark = [pytest.mark.asyncio, needs_db]

# Senhas de fixture liberadas no .gitleaks.toml (#33).
PASSWORD = "senhaForte123"
NEW_PASSWORD = "outraSenha456"
LOGIN_ERROR = "E-mail ou senha incorretos"
FORGOT_MESSAGE = "Se o e-mail existir, um link de recuperação será enviado."
CLIENT_ACCESS_SECONDS = 30 * 60
STAFF_ACCESS_SECONDS = 12 * 60 * 60


# ── apoio ───────────────────────────────────────────────


async def register(client, email="pessoa@teste.com", password=PASSWORD, full_name="Pessoa", **extra):
    return await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name, **extra},
    )


async def register_ok(client, email="pessoa@teste.com", **kwargs):
    response = await register(client, email=email, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


async def login(client, email="pessoa@teste.com", password=PASSWORD):
    return await client.post("/api/auth/login", json={"email": email, "password": password})


async def add_user(maker, email, role=UserRole.CLIENT, password=PASSWORD, is_active=True):
    """Grava um usuário direto no banco, com a senha em bcrypt."""
    async with maker() as db:
        user = User(
            email=email,
            hashed_password=security.get_password_hash(password),
            full_name=email.split("@")[0],
            role=role,
            is_active=is_active,
        )
        db.add(user)
        await db.commit()
        return user


async def get_user(maker, email):
    async with maker() as db:
        return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()


async def count_users(maker):
    async with maker() as db:
        return (await db.execute(select(func.count()).select_from(User))).scalar_one()


async def tokens_of(maker, model, email):
    async with maker() as db:
        stmt = select(model).join(User, model.user_id == User.id).where(User.email == email)
        return list((await db.execute(stmt)).scalars())


async def expire_tokens(maker, model):
    async with maker() as db:
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db.execute(update(model).values(expires_at=past))
        await db.commit()


def decode(token):
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def make_token(claims, key=None, expires_in=timedelta(minutes=5)):
    payload = {"exp": datetime.now(timezone.utc) + expires_in, **claims}
    return jwt.encode(payload, key or settings.secret_key, algorithm=settings.algorithm)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def seconds_until(exp):
    return exp - datetime.now(timezone.utc).timestamp()


def refresh_cookie_header(response):
    cookies = [v for k, v in response.headers.multi_items() if k.lower() == "set-cookie"]
    matches = [c for c in cookies if c.startswith("refresh_token=")]
    assert len(matches) == 1, cookies
    return matches[0]


def refresh_token_from(response):
    return refresh_cookie_header(response).split(";", 1)[0].split("=", 1)[1]


# ── cadastro ────────────────────────────────────────────


async def test_cadastro_devolve_tokens_e_usuario_sem_senha(sessionmaker, client):
    response = await register(client, phone="(91) 99999-0000")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    user = body["user"]
    assert user["email"] == "pessoa@teste.com"
    assert user["full_name"] == "Pessoa"
    assert user["phone"] == "(91) 99999-0000"
    assert user["is_active"] is True
    assert user["email_verified"] is False
    assert uuid.UUID(user["id"])
    assert "password" not in user and "hashed_password" not in user


async def test_cadastro_grava_refresh_token_em_cookie_http_only(sessionmaker, client):
    response = await register(client)

    cookie = refresh_cookie_header(response).lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert decode(refresh_token_from(response))["type"] == "refresh"


async def test_cadastro_guarda_so_o_hash_bcrypt_da_senha(sessionmaker, client):
    await register_ok(client)

    user = await get_user(sessionmaker, "pessoa@teste.com")
    assert user.hashed_password != PASSWORD
    assert user.hashed_password.startswith("$2")
    assert bcrypt.checkpw(PASSWORD.encode(), user.hashed_password.encode())


async def test_primeiro_usuario_vira_admin_e_os_seguintes_viram_cliente(sessionmaker, client):
    first = await register_ok(client, email="dono@teste.com")
    second = await register_ok(client, email="cliente@teste.com")
    third = await register_ok(client, email="outro@teste.com")

    assert first["user"]["role"] == "admin"
    assert second["user"]["role"] == "client"
    assert third["user"]["role"] == "client"


async def test_cadastro_tira_espacos_das_pontas_do_nome(sessionmaker, client):
    body = await register_ok(client, full_name="   Maria Souza  ")

    assert body["user"]["full_name"] == "Maria Souza"
    assert (await get_user(sessionmaker, "pessoa@teste.com")).full_name == "Maria Souza"


async def test_cadastro_cria_token_de_verificacao_que_vence_em_24_horas(sessionmaker, client):
    await register_ok(client)

    tokens = await tokens_of(sessionmaker, EmailVerificationToken, "pessoa@teste.com")
    assert len(tokens) == 1
    token = tokens[0]
    assert token.is_used is False
    assert uuid.UUID(token.token)
    remaining = token.expires_at - datetime.now(timezone.utc)
    assert timedelta(hours=23, minutes=59) < remaining <= timedelta(hours=24)


async def test_cadastro_com_email_repetido_responde_400(sessionmaker, client):
    await register_ok(client)

    response = await register(client, full_name="Outra Pessoa")

    assert response.status_code == 400
    assert response.json()["detail"] == "Email já cadastrado."
    assert await count_users(sessionmaker) == 1


@pytest.mark.parametrize(
    "password",
    ["abc1234", "somenteletras", "1234567890", ""],
    ids=["menos-de-8", "sem-numero", "sem-letra", "vazia"],
)
async def test_cadastro_com_senha_fraca_responde_422(password, sessionmaker, client):
    response = await register(client, password=password)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    assert await count_users(sessionmaker) == 0


@pytest.mark.parametrize("full_name", ["A", "  B  ", ""], ids=["uma-letra", "uma-letra-com-espacos", "vazio"])
async def test_cadastro_com_nome_curto_responde_422(full_name, sessionmaker, client):
    response = await register(client, full_name=full_name)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "full_name"]
    assert await count_users(sessionmaker) == 0


@pytest.mark.parametrize("email", ["sem-arroba", "pessoa@", "@teste.com", "pessoa@@teste.com"])
async def test_cadastro_com_email_invalido_responde_422(email, sessionmaker, client):
    response = await register(client, email=email)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "email"]
    assert await count_users(sessionmaker) == 0


@pytest.mark.parametrize("missing", ["email", "password", "full_name"])
async def test_cadastro_sem_campo_obrigatorio_responde_422(missing, sessionmaker, client):
    payload = {"email": "pessoa@teste.com", "password": PASSWORD, "full_name": "Pessoa"}
    del payload[missing]

    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 422
    assert await count_users(sessionmaker) == 0


# ── tokens ──────────────────────────────────────────────


async def test_access_token_do_cadastro_traz_id_email_e_perfil(sessionmaker, client):
    body = await register_ok(client)

    claims = decode(body["access_token"])
    assert claims["user_id"] == body["user"]["id"]
    assert claims["email"] == "pessoa@teste.com"
    assert claims["role"] == "admin"
    assert "type" not in claims


async def test_access_token_de_cliente_vence_em_30_minutos(sessionmaker, client):
    await add_user(sessionmaker, "dono@teste.com", role=UserRole.ADMIN)
    body = await register_ok(client)

    assert body["user"]["role"] == "client"
    assert body["expires_in"] == CLIENT_ACCESS_SECONDS
    remaining = seconds_until(decode(body["access_token"])["exp"])
    assert CLIENT_ACCESS_SECONDS - 60 < remaining <= CLIENT_ACCESS_SECONDS


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.BARBER])
async def test_access_token_de_equipe_vence_em_12_horas(role, sessionmaker, client):
    await add_user(sessionmaker, "equipe@teste.com", role=role)

    body = (await login(client, "equipe@teste.com")).json()

    assert body["user"]["role"] == role.value
    assert body["expires_in"] == STAFF_ACCESS_SECONDS
    remaining = seconds_until(decode(body["access_token"])["exp"])
    assert STAFF_ACCESS_SECONDS - 60 < remaining <= STAFF_ACCESS_SECONDS


@pytest.mark.parametrize(
    ("role", "days"),
    [(UserRole.CLIENT, 7), (UserRole.BARBER, 30), (UserRole.ADMIN, 30)],
)
async def test_refresh_token_vence_conforme_o_perfil(role, days, sessionmaker, client):
    await add_user(sessionmaker, "alguem@teste.com", role=role)

    response = await login(client, "alguem@teste.com")

    claims = decode(refresh_token_from(response))
    assert claims["type"] == "refresh"
    assert claims["role"] == role.value
    remaining = seconds_until(claims["exp"])
    assert days * 86400 - 60 < remaining <= days * 86400


# ── login ───────────────────────────────────────────────


async def test_login_com_credenciais_certas_devolve_tokens(sessionmaker, client):
    registered = await register_ok(client)

    response = await login(client)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["id"] == registered["user"]["id"]
    assert decode(body["access_token"])["user_id"] == registered["user"]["id"]
    assert "httponly" in refresh_cookie_header(response).lower()


@pytest.mark.parametrize(
    ("email", "password"),
    [("pessoa@teste.com", "senhaErrada999"), ("ninguem@teste.com", PASSWORD)],
    ids=["senha-errada", "email-desconhecido"],
)
async def test_login_invalido_responde_401_com_mensagem_generica(email, password, sessionmaker, client):
    await register_ok(client)

    response = await login(client, email, password)

    assert response.status_code == 401
    assert response.json()["detail"] == LOGIN_ERROR
    assert response.headers["www-authenticate"] == "Bearer"
    assert "set-cookie" not in response.headers


async def test_login_diferencia_maiusculas_no_email(sessionmaker, client):
    await register_ok(client)

    response = await login(client, "PESSOA@teste.com")

    assert response.status_code == 401


async def test_usuario_desativado_nao_consegue_entrar(sessionmaker, client):
    await add_user(sessionmaker, "inativo@teste.com", is_active=False)

    response = await login(client, "inativo@teste.com")

    assert response.status_code == 401
    assert response.json()["detail"] == LOGIN_ERROR


async def test_login_com_hash_corrompido_responde_401(sessionmaker, client):
    async with sessionmaker() as db:
        db.add(User(email="quebrado@teste.com", hashed_password="nao-e-bcrypt", full_name="Quebrado"))
        await db.commit()

    response = await login(client, "quebrado@teste.com")

    assert response.status_code == 401


async def test_login_sem_senha_responde_422(sessionmaker, client):
    response = await client.post("/api/auth/login", json={"email": "pessoa@teste.com"})

    assert response.status_code == 422


# ── /me e rotas protegidas ──────────────────────────────


async def test_me_devolve_o_usuario_do_token_sem_senha(sessionmaker, client):
    body = await register_ok(client)

    response = await client.get("/api/auth/me", headers=bearer(body["access_token"]))

    assert response.status_code == 200, response.text
    me = response.json()
    assert me["id"] == body["user"]["id"]
    assert me["email"] == "pessoa@teste.com"
    assert me["role"] == "admin"
    assert "password" not in me and "hashed_password" not in me


async def test_me_com_token_do_login_devolve_o_mesmo_usuario(sessionmaker, client):
    user = await add_user(sessionmaker, "barbeiro@teste.com", role=UserRole.BARBER)
    token = (await login(client, "barbeiro@teste.com")).json()["access_token"]

    response = await client.get("/api/auth/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["role"] == "barber"


async def test_me_sem_token_responde_403(sessionmaker, client):
    response = await client.get("/api/auth/me")

    assert response.status_code == 403


async def test_me_com_esquema_diferente_de_bearer_responde_403(sessionmaker, client):
    body = await register_ok(client)

    response = await client.get("/api/auth/me", headers={"Authorization": f"Basic {body['access_token']}"})

    assert response.status_code == 403


async def test_me_com_token_malformado_responde_401(sessionmaker, client):
    response = await client.get("/api/auth/me", headers=bearer("isto-nao-e-um-jwt"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido ou expirado."
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_com_token_assinado_com_outra_chave_responde_401(sessionmaker, client):
    user = await add_user(sessionmaker, "pessoa@teste.com")
    token = make_token({"user_id": str(user.id), "role": "client"}, key="outra-chave-qualquer")

    response = await client.get("/api/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido ou expirado."


async def test_me_com_token_vencido_responde_401(sessionmaker, client):
    user = await add_user(sessionmaker, "pessoa@teste.com")
    token = make_token({"user_id": str(user.id), "role": "client"}, expires_in=timedelta(minutes=-1))

    response = await client.get("/api/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido ou expirado."


async def test_refresh_token_nao_serve_como_access_token(sessionmaker, client):
    await register_ok(client)
    refresh_token = refresh_token_from(await login(client))

    response = await client.get("/api/auth/me", headers=bearer(refresh_token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token não pode ser usado para acesso."


@pytest.mark.parametrize(
    "claims",
    [{"role": "client"}, {"user_id": "", "role": "client"}, {"user_id": "nao-e-uuid", "role": "client"}],
    ids=["sem-user-id", "user-id-vazio", "user-id-invalido"],
)
async def test_me_com_payload_invalido_responde_401(claims, sessionmaker, client):
    response = await client.get("/api/auth/me", headers=bearer(make_token(claims)))

    assert response.status_code == 401
    assert response.json()["detail"] == "Payload inválido."


async def test_me_de_usuario_que_nao_existe_mais_responde_401(sessionmaker, client):
    token = make_token({"user_id": str(uuid.uuid4()), "role": "client"})

    response = await client.get("/api/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Usuário não encontrado."


async def test_me_de_usuario_desativado_depois_do_login_responde_403(sessionmaker, client):
    body = await register_ok(client)
    async with sessionmaker() as db:
        await db.execute(update(User).values(is_active=False))
        await db.commit()

    response = await client.get("/api/auth/me", headers=bearer(body["access_token"]))

    assert response.status_code == 403
    assert response.json()["detail"] == "Usuário inativo."


# ── perfis ──────────────────────────────────────────────


def user_with(role):
    return User(email=f"{role.value}@teste.com", hashed_password="x", full_name="Alguém", role=role)


async def test_get_current_admin_aceita_so_admin():
    admin = user_with(UserRole.ADMIN)
    assert await get_current_admin(admin) is admin

    for role in (UserRole.BARBER, UserRole.CLIENT):
        with pytest.raises(HTTPException) as error:
            await get_current_admin(user_with(role))
        assert error.value.status_code == 403
        assert error.value.detail == "Acesso restrito para administradores."


async def test_get_current_barber_or_admin_recusa_cliente():
    for role in (UserRole.ADMIN, UserRole.BARBER):
        user = user_with(role)
        assert await get_current_barber_or_admin(user) is user

    with pytest.raises(HTTPException) as error:
        await get_current_barber_or_admin(user_with(UserRole.CLIENT))
    assert error.value.status_code == 403
    assert error.value.detail == "Acesso restrito para barbeiros ou administradores."


# ── logout ──────────────────────────────────────────────


async def test_logout_apaga_o_cookie_do_refresh_token(sessionmaker, client):
    response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"] == "Logout efetuado com sucesso."
    cookie = refresh_cookie_header(response).lower()
    assert cookie.startswith('refresh_token="";') or cookie.startswith("refresh_token=;")
    assert "max-age=0" in cookie


# ── verificação de e-mail ───────────────────────────────


async def verification_token(maker, email="pessoa@teste.com"):
    (token,) = await tokens_of(maker, EmailVerificationToken, email)
    return token.token


async def test_verificacao_marca_o_email_e_usa_o_token(sessionmaker, client):
    await register_ok(client)
    token = await verification_token(sessionmaker)

    response = await client.post("/api/auth/verify-email", json={"token": token})

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "E-mail verificado com sucesso."
    assert (await get_user(sessionmaker, "pessoa@teste.com")).email_verified is True
    (stored,) = await tokens_of(sessionmaker, EmailVerificationToken, "pessoa@teste.com")
    assert stored.is_used is True


async def test_verificacao_aparece_no_me(sessionmaker, client):
    body = await register_ok(client)
    await client.post("/api/auth/verify-email", json={"token": await verification_token(sessionmaker)})

    response = await client.get("/api/auth/me", headers=bearer(body["access_token"]))

    assert response.json()["email_verified"] is True


async def test_verificacao_so_marca_o_dono_do_token(sessionmaker, client):
    await register_ok(client, email="a@teste.com")
    await register_ok(client, email="b@teste.com")

    await client.post("/api/auth/verify-email", json={"token": await verification_token(sessionmaker, "a@teste.com")})

    assert (await get_user(sessionmaker, "a@teste.com")).email_verified is True
    assert (await get_user(sessionmaker, "b@teste.com")).email_verified is False


async def test_token_de_verificacao_nao_pode_ser_reusado(sessionmaker, client):
    await register_ok(client)
    token = await verification_token(sessionmaker)
    assert (await client.post("/api/auth/verify-email", json={"token": token})).status_code == 200

    response = await client.post("/api/auth/verify-email", json={"token": token})

    assert response.status_code == 400
    assert response.json()["detail"] == "Token inválido ou expirado."


async def test_token_de_verificacao_vencido_responde_400(sessionmaker, client):
    await register_ok(client)
    token = await verification_token(sessionmaker)
    await expire_tokens(sessionmaker, EmailVerificationToken)

    response = await client.post("/api/auth/verify-email", json={"token": token})

    assert response.status_code == 400
    assert (await get_user(sessionmaker, "pessoa@teste.com")).email_verified is False


async def test_token_de_verificacao_desconhecido_responde_400(sessionmaker, client):
    await register_ok(client)

    response = await client.post("/api/auth/verify-email", json={"token": str(uuid.uuid4())})

    assert response.status_code == 400
    assert (await get_user(sessionmaker, "pessoa@teste.com")).email_verified is False


# ── redefinição de senha ────────────────────────────────


async def forgot(client, email="pessoa@teste.com"):
    return await client.post("/api/auth/forgot-password", json={"email": email})


async def reset_token(maker, email="pessoa@teste.com"):
    tokens = await tokens_of(maker, PasswordResetToken, email)
    assert len(tokens) == 1
    return tokens[0]


async def reset(client, token, new_password=NEW_PASSWORD):
    return await client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": new_password}
    )


@pytest.mark.parametrize("email", ["pessoa@teste.com", "ninguem@teste.com"], ids=["cadastrado", "desconhecido"])
async def test_esqueci_a_senha_responde_igual_para_qualquer_email(email, sessionmaker, client):
    await register_ok(client)

    response = await forgot(client, email)

    assert response.status_code == 200
    assert response.json()["message"] == FORGOT_MESSAGE


async def test_esqueci_a_senha_cria_token_de_uma_hora_so_para_email_cadastrado(sessionmaker, client):
    await register_ok(client)

    await forgot(client, "ninguem@teste.com")
    async with sessionmaker() as db:
        assert (await db.execute(select(func.count()).select_from(PasswordResetToken))).scalar_one() == 0

    await forgot(client)
    token = await reset_token(sessionmaker)
    assert token.is_used is False
    remaining = token.expires_at - datetime.now(timezone.utc)
    assert timedelta(minutes=59) < remaining <= timedelta(hours=1)


async def test_esqueci_a_senha_com_email_invalido_responde_422(sessionmaker, client):
    response = await forgot(client, "sem-arroba")

    assert response.status_code == 422


async def test_redefinicao_troca_a_senha(sessionmaker, client):
    await register_ok(client)
    await forgot(client)
    token = await reset_token(sessionmaker)

    response = await reset(client, token.token)

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Senha redefinida com sucesso."
    assert (await login(client, password=NEW_PASSWORD)).status_code == 200
    assert (await login(client, password=PASSWORD)).status_code == 401
    assert (await reset_token(sessionmaker)).is_used is True


async def test_token_de_redefinicao_nao_pode_ser_reusado(sessionmaker, client):
    await register_ok(client)
    await forgot(client)
    token = (await reset_token(sessionmaker)).token
    assert (await reset(client, token)).status_code == 200

    response = await reset(client, token, new_password="terceiraSenha789")

    assert response.status_code == 400
    assert response.json()["detail"] == "Token de reset inválido ou expirado."
    assert (await login(client, password=NEW_PASSWORD)).status_code == 200


async def test_token_de_redefinicao_vencido_responde_400(sessionmaker, client):
    await register_ok(client)
    await forgot(client)
    token = (await reset_token(sessionmaker)).token
    await expire_tokens(sessionmaker, PasswordResetToken)

    response = await reset(client, token)

    assert response.status_code == 400
    assert (await login(client)).status_code == 200


async def test_token_de_redefinicao_desconhecido_responde_400(sessionmaker, client):
    await register_ok(client)

    response = await reset(client, str(uuid.uuid4()))

    assert response.status_code == 400
    assert (await login(client)).status_code == 200


async def test_token_de_verificacao_nao_serve_para_redefinir_a_senha(sessionmaker, client):
    await register_ok(client)

    response = await reset(client, await verification_token(sessionmaker))

    assert response.status_code == 400
    assert (await login(client)).status_code == 200


@pytest.mark.parametrize(
    "new_password",
    ["abc1234", "somenteletras", "1234567890"],
    ids=["menos-de-8", "sem-numero", "sem-letra"],
)
async def test_redefinicao_com_senha_fraca_responde_422(new_password, sessionmaker, client):
    await register_ok(client)
    await forgot(client)
    token = await reset_token(sessionmaker)

    response = await reset(client, token.token, new_password=new_password)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "new_password"]
    assert (await reset_token(sessionmaker)).is_used is False
    assert (await login(client)).status_code == 200


async def test_cada_pedido_gera_um_token_novo_e_os_dois_valem(sessionmaker, client):
    await register_ok(client)
    await forgot(client)
    await forgot(client)

    tokens = await tokens_of(sessionmaker, PasswordResetToken, "pessoa@teste.com")
    assert len(tokens) == 2
    assert tokens[0].token != tokens[1].token
    assert (await reset(client, tokens[1].token)).status_code == 200
    # Hoje o pedido novo não invalida o anterior: o primeiro token ainda troca a senha.
    assert (await reset(client, tokens[0].token, new_password="terceiraSenha789")).status_code == 200
    assert (await login(client, password="terceiraSenha789")).status_code == 200
