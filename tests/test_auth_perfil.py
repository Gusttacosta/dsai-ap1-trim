"""
Testes do perfil (`PUT /api/auth/me`) e da troca de senha (`PUT /api/auth/me/password`) (#35).

Spec: SPEC/2026-11-22-auth-perfil-senha.md
"""

import pytest
from sqlalchemy import select

from src.backend.modules.auth import security
from src.backend.modules.auth.models import PasswordResetToken, User, UserRole
from src.backend.modules.auth.service import AuthService
from tests.agenda_fixtures import needs_db
from tests.test_auth_integracao import (
    NEW_PASSWORD,
    PASSWORD,
    add_user,
    bearer,
    get_user,
    login,
    make_token,
    refresh_token_from,
    register,
)
from tests.test_auth_refresh import refresh, with_cookie

pytestmark = [pytest.mark.asyncio, needs_db]

EMAIL = "cliente@teste.com"


# ── apoio ───────────────────────────────────────────────


async def logged_in(maker, client, email=EMAIL, role=UserRole.CLIENT):
    """Cria o usuário e faz login. Devolve o cabeçalho Authorization e o refresh token."""
    await add_user(maker, email, role)
    response = await login(client, email)
    assert response.status_code == 200, response.text
    return bearer(response.json()["access_token"]), refresh_token_from(response)


async def update_me(client, headers, body):
    return await client.put("/api/auth/me", json=body, headers=headers)


async def change_password(client, headers, current=PASSWORD, new=NEW_PASSWORD, cookie=None):
    if cookie is not None:
        headers = with_cookie(cookie, **headers)
    return await client.put(
        "/api/auth/me/password",
        json={"current_password": current, "new_password": new},
        headers=headers,
    )


def error_messages(response):
    return " | ".join(d["msg"] for d in response.json()["detail"])


# ── perfil: atualização parcial ─────────────────────────


async def test_atualiza_os_campos_enviados_e_devolve_o_usuario(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)
    before = await get_user(sessionmaker, EMAIL)

    response = await update_me(
        client,
        headers,
        {"full_name": "Maria Souza", "phone": "91999990000", "avatar_url": "https://cdn.exemplo.com/eu.png"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "Maria Souza"
    assert body["phone"] == "(91) 99999-0000"
    assert body["avatar_url"] == "https://cdn.exemplo.com/eu.png"
    assert body["email"] == EMAIL
    assert "hashed_password" not in body
    saved = await get_user(sessionmaker, EMAIL)
    assert (saved.full_name, saved.phone, saved.avatar_url) == (
        "Maria Souza",
        "(91) 99999-0000",
        "https://cdn.exemplo.com/eu.png",
    )
    assert saved.updated_at > before.updated_at


async def test_campos_nao_enviados_continuam_iguais(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)
    await update_me(client, headers, {"phone": "(91) 3333-0000", "avatar_url": "https://a.com/f.jpg"})

    response = await update_me(client, headers, {"full_name": "Outro Nome"})

    assert response.status_code == 200
    saved = await get_user(sessionmaker, EMAIL)
    assert saved.full_name == "Outro Nome"
    assert saved.phone == "(91) 3333-0000"
    assert saved.avatar_url == "https://a.com/f.jpg"


async def test_corpo_vazio_nao_muda_nada(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)
    before = await get_user(sessionmaker, EMAIL)

    response = await update_me(client, headers, {})

    assert response.status_code == 200
    after = await get_user(sessionmaker, EMAIL)
    assert (after.full_name, after.phone, after.updated_at) == (
        before.full_name,
        before.phone,
        before.updated_at,
    )


async def test_get_me_mostra_o_perfil_atualizado(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)
    await update_me(client, headers, {"full_name": "  Nome Com Espaço  "})

    me = await client.get("/api/auth/me", headers=headers)

    assert me.json()["full_name"] == "Nome Com Espaço"


# ── perfil: nome ────────────────────────────────────────


@pytest.mark.parametrize("name", ["A", "  B  ", "x" * 256, None])
async def test_nome_invalido_responde_422_e_nao_muda(sessionmaker, client, name):
    headers, _ = await logged_in(sessionmaker, client)
    before = (await get_user(sessionmaker, EMAIL)).full_name

    response = await update_me(client, headers, {"full_name": name})

    assert response.status_code == 422
    assert (await get_user(sessionmaker, EMAIL)).full_name == before


async def test_nome_com_255_caracteres_e_aceito(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)

    response = await update_me(client, headers, {"full_name": "n" * 255})

    assert response.status_code == 200
    assert len((await get_user(sessionmaker, EMAIL)).full_name) == 255


# ── perfil: telefone ────────────────────────────────────


@pytest.mark.parametrize(
    ("typed", "saved"),
    [
        ("(91) 99999-0000", "(91) 99999-0000"),
        ("91999990000", "(91) 99999-0000"),
        ("91 99999 0000", "(91) 99999-0000"),
        ("+55 (11) 98765-4321", "(11) 98765-4321"),
        ("+5511987654321", "(11) 98765-4321"),
        ("(91) 3333-0000", "(91) 3333-0000"),
        ("9133330000", "(91) 3333-0000"),
        ("  (21) 2222-1111  ", "(21) 2222-1111"),
    ],
)
async def test_telefone_valido_e_normalizado(sessionmaker, client, typed, saved):
    headers, _ = await logged_in(sessionmaker, client)

    response = await update_me(client, headers, {"phone": typed})

    assert response.status_code == 200, response.text
    assert response.json()["phone"] == saved
    assert (await get_user(sessionmaker, EMAIL)).phone == saved


@pytest.mark.parametrize("empty", [None, "", "   "])
async def test_telefone_vazio_apaga_o_telefone(sessionmaker, client, empty):
    headers, _ = await logged_in(sessionmaker, client)
    await update_me(client, headers, {"phone": "91999990000"})

    response = await update_me(client, headers, {"phone": empty})

    assert response.status_code == 200
    assert (await get_user(sessionmaker, EMAIL)).phone is None


@pytest.mark.parametrize(
    ("typed", "message"),
    [
        ("(01) 99999-0000", "DDD não pode começar com 0"),
        ("9999-0000", "DDD e 8 dígitos"),
        ("919999900001", "DDD e 8 dígitos"),
        ("(91) 89999-0000", "Celular deve começar com 9"),
        ("91 9999a-0000", "só números"),
        ("91+999990000", "só números"),
        ("+1 415 555 0000", "brasileiro"),
        ("9" * 30, "DDD e 8 dígitos"),
    ],
)
async def test_telefone_invalido_responde_422(sessionmaker, client, typed, message):
    headers, _ = await logged_in(sessionmaker, client)

    response = await update_me(client, headers, {"phone": typed})

    assert response.status_code == 422
    assert message in error_messages(response)
    assert (await get_user(sessionmaker, EMAIL)).phone is None


# ── perfil: foto ────────────────────────────────────────


@pytest.mark.parametrize("url", ["https://cdn.exemplo.com/a.png", "http://exemplo.com/f?x=1"])
async def test_url_da_foto_http_ou_https_e_aceita(sessionmaker, client, url):
    headers, _ = await logged_in(sessionmaker, client)

    response = await update_me(client, headers, {"avatar_url": url})

    assert response.status_code == 200
    assert (await get_user(sessionmaker, EMAIL)).avatar_url == url


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "ftp://exemplo.com/a.png", "https://", "foto.png", "https://a.com/" + "x" * 2040],
)
async def test_url_da_foto_invalida_responde_422(sessionmaker, client, url):
    headers, _ = await logged_in(sessionmaker, client)

    response = await update_me(client, headers, {"avatar_url": url})

    assert response.status_code == 422
    assert (await get_user(sessionmaker, EMAIL)).avatar_url is None


async def test_foto_vazia_apaga_a_foto(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)
    await update_me(client, headers, {"avatar_url": "https://a.com/f.png"})

    response = await update_me(client, headers, {"avatar_url": ""})

    assert response.status_code == 200
    assert (await get_user(sessionmaker, EMAIL)).avatar_url is None


# ── perfil: campos proibidos e acesso ───────────────────


@pytest.mark.parametrize(
    "body",
    [
        {"role": "admin"},
        {"email": "novo@teste.com"},
        {"is_active": False},
        {"full_name": "Nome Válido", "role": "admin"},
    ],
)
async def test_campos_fora_da_lista_respondem_422(sessionmaker, client, body):
    headers, _ = await logged_in(sessionmaker, client)

    response = await update_me(client, headers, body)

    assert response.status_code == 422
    saved = await get_user(sessionmaker, EMAIL)
    assert (saved.role, saved.email, saved.is_active, saved.full_name) == (
        UserRole.CLIENT,
        EMAIL,
        True,
        "cliente",
    )


@pytest.mark.parametrize("route", ["/api/auth/me", "/api/auth/me/password"])
async def test_rotas_sem_token_respondem_403(sessionmaker, client, route):
    response = await client.put(route, json={})

    assert response.status_code == 403


@pytest.mark.parametrize("route", ["/api/auth/me", "/api/auth/me/password"])
async def test_rotas_com_token_invalido_respondem_401(sessionmaker, client, route):
    token = make_token({"user_id": "x"}, key="outra-chave-de-teste")

    response = await client.put(route, json={}, headers=bearer(token))

    assert response.status_code == 401


async def test_barbeiro_tambem_atualiza_o_proprio_perfil(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client, "barbeiro@teste.com", UserRole.BARBER)

    response = await update_me(client, headers, {"full_name": "Barbeiro Novo"})

    assert response.status_code == 200
    assert response.json()["role"] == "barber"


# ── cadastro usa as mesmas regras ───────────────────────


async def test_cadastro_normaliza_o_telefone(sessionmaker, client):
    response = await register(client, EMAIL, phone="+55 91 99999 0000")

    assert response.status_code == 201, response.text
    assert response.json()["user"]["phone"] == "(91) 99999-0000"


@pytest.mark.parametrize(
    "extra",
    [{"phone": "(01) 99999-0000"}, {"phone": "x" * 25}, {"full_name": "n" * 256}],
)
async def test_cadastro_recusa_telefone_ou_nome_invalido_com_422(sessionmaker, client, extra):
    response = await register(client, EMAIL, **extra)

    assert response.status_code == 422
    assert await get_user(sessionmaker, EMAIL) is None


# ── troca de senha ──────────────────────────────────────


async def test_troca_a_senha_e_o_login_passa_a_usar_a_nova(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)

    response = await change_password(client, headers)

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Senha alterada. As outras sessões foram encerradas."
    assert (await login(client, EMAIL, PASSWORD)).status_code == 401
    assert (await login(client, EMAIL, NEW_PASSWORD)).status_code == 200
    saved = await get_user(sessionmaker, EMAIL)
    assert saved.hashed_password.startswith("$2")
    assert security.verify_password(NEW_PASSWORD, saved.hashed_password)


async def test_senha_atual_errada_responde_400_e_nao_troca(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)

    response = await change_password(client, headers, current="senhaErrada999")

    assert response.status_code == 400
    assert response.json()["detail"] == "Senha atual incorreta."
    assert (await login(client, EMAIL, PASSWORD)).status_code == 200


async def test_senha_nova_igual_a_atual_responde_400(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)

    response = await change_password(client, headers, new=PASSWORD)

    assert response.status_code == 400
    assert response.json()["detail"] == "A nova senha precisa ser diferente da atual."


@pytest.mark.parametrize(
    ("weak", "message"),
    [
        ("curta1", "ter no mínimo 8 caracteres"),
        ("somenteletras", "conter pelo menos 1 número"),
        ("12345678", "conter pelo menos 1 letra"),
    ],
)
async def test_senha_nova_fraca_responde_422(sessionmaker, client, weak, message):
    headers, _ = await logged_in(sessionmaker, client)

    response = await change_password(client, headers, new=weak)

    assert response.status_code == 422
    assert f"Nova senha deve {message}" in error_messages(response)
    assert (await login(client, EMAIL, PASSWORD)).status_code == 200


async def test_troca_encerra_as_outras_sessoes_e_mantem_a_do_cookie(sessionmaker, client):
    headers, this_device = await logged_in(sessionmaker, client)
    other_device = refresh_token_from(await login(client, EMAIL))
    _, someone_else = await logged_in(sessionmaker, client, "outra@teste.com")

    response = await change_password(client, headers, cookie=this_device)

    assert response.status_code == 200
    assert (await refresh(client, other_device)).status_code == 401
    assert (await refresh(client, this_device)).status_code == 200
    assert (await refresh(client, someone_else)).status_code == 200


async def test_troca_sem_cookie_encerra_todas_as_sessoes(sessionmaker, client):
    headers, first = await logged_in(sessionmaker, client)
    second = refresh_token_from(await login(client, EMAIL))

    await change_password(client, headers)

    assert (await refresh(client, first)).status_code == 401
    assert (await refresh(client, second)).status_code == 401


async def test_cookie_de_outro_usuario_nao_preserva_sessao_nenhuma(sessionmaker, client):
    headers, mine = await logged_in(sessionmaker, client)
    _, theirs = await logged_in(sessionmaker, client, "outra@teste.com")

    await change_password(client, headers, cookie=theirs)

    assert (await refresh(client, mine)).status_code == 401
    assert (await refresh(client, theirs)).status_code == 200


async def test_troca_invalida_os_tokens_de_redefinicao_pendentes(sessionmaker, client):
    headers, _ = await logged_in(sessionmaker, client)
    async with sessionmaker() as db:
        pending = await AuthService(db).create_password_reset_token(EMAIL)

    await change_password(client, headers)
    reset = await client.post(
        "/api/auth/reset-password", json={"token": pending, "new_password": "terceiraSenha789"}
    )

    assert reset.status_code == 400
    assert (await login(client, EMAIL, NEW_PASSWORD)).status_code == 200
    async with sessionmaker() as db:
        tokens = (await db.execute(select(PasswordResetToken))).scalars().all()
    assert [t.is_used for t in tokens] == [True]


async def test_senha_errada_nao_encerra_sessoes(sessionmaker, client):
    headers, session = await logged_in(sessionmaker, client)

    await change_password(client, headers, current="senhaErrada999")

    assert (await refresh(client, session)).status_code == 200
    async with sessionmaker() as db:
        assert (await db.execute(select(User))).scalars().one().is_active
