"""
Auth: reenvio da verificação de e-mail, administração de usuários, limite de tentativas de login e
token de redefinição único (#35).

Spec: SPEC/2026-11-25-auth-admin-usuarios.md
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.auth import security
from src.backend.modules.auth.models import EmailVerificationToken, RefreshToken, User, UserRole
from tests.agenda_fixtures import needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/auth"
PASSWORD = "senhaForte123"
TOO_MANY = "Muitas tentativas de login. Tente de novo em alguns minutos."


async def user_with_password(maker, email, role=UserRole.CLIENT, *, full_name=None, verified=True, active=True):
    async with maker() as db:
        user = User(
            email=email, hashed_password=security.get_password_hash(PASSWORD),
            full_name=full_name or email.split("@")[0].capitalize(), role=role,
            email_verified=verified, is_active=active,
        )
        db.add(user)
        await db.commit()
        return user


async def login(client, email, password=PASSWORD):
    return await client.post(f"{URL}/login", json={"email": email, "password": password})


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN, full_name="Dono")


# ── reenvio da verificação ──────────────────────────────


async def verification_tokens(maker, user_id):
    async with maker() as db:
        rows = await db.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.user_id == user_id)
            .order_by(EmailVerificationToken.created_at)
        )
        return list(rows.scalars().all())


async def test_resend_creates_a_new_token_and_retires_the_old(client, sessionmaker):
    response = await client.post(f"{URL}/register", json={
        "email": "pessoa@teste.com", "password": PASSWORD, "full_name": "Pessoa Teste"})
    assert response.status_code == 201, response.text
    async with sessionmaker() as db:
        user = (await db.execute(select(User).where(User.email == "pessoa@teste.com"))).scalar_one()

    response = await client.post(f"{URL}/verify-email/resend", json={"email": "pessoa@teste.com"})

    assert response.status_code == 200
    old, new = await verification_tokens(sessionmaker, user.id)
    assert (old.is_used, new.is_used) == (True, False)
    assert (await client.post(f"{URL}/verify-email", json={"token": old.token})).status_code == 400
    assert (await client.post(f"{URL}/verify-email", json={"token": new.token})).status_code == 200


@pytest.mark.parametrize("case", ["desconhecido", "ja-verificado", "desativado"])
async def test_resend_answers_the_same_without_creating_tokens(client, sessionmaker, case):
    email = "ninguem@teste.com"
    if case == "ja-verificado":
        await user_with_password(sessionmaker, email, verified=True)
    elif case == "desativado":
        await user_with_password(sessionmaker, email, verified=False, active=False)

    response = await client.post(f"{URL}/verify-email/resend", json={"email": email})

    assert response.status_code == 200
    assert response.json()["message"] == "Se a conta existir e ainda não estiver verificada, um novo link será enviado."
    async with sessionmaker() as db:
        assert (await db.execute(select(EmailVerificationToken))).first() is None


async def test_resend_with_invalid_email_gets_422(client, sessionmaker):
    assert (await client.post(f"{URL}/verify-email/resend", json={"email": "nao-e-email"})).status_code == 422


# ── administração de usuários ───────────────────────────


@pytest_asyncio.fixture
async def people(sessionmaker, admin):
    ana = await add_user(sessionmaker, "ana@teste.com", full_name="Ana Lima")
    bruno = await add_user(sessionmaker, "bruno@teste.com", UserRole.BARBER, full_name="Bruno Reis")
    caio = await add_user(sessionmaker, "caio@teste.com", full_name="Caio Melo", is_active=False)
    return {"admin": admin, "ana": ana, "bruno": bruno, "caio": caio}


async def listing(client, admin, **params):
    response = await client.get(f"{URL}/users", params=params, headers=auth(admin))
    assert response.status_code == 200, response.text
    return response.json()


async def test_admin_lists_users_with_pagination(client, people):
    body = await listing(client, people["admin"], per_page=2)
    assert (body["total"], body["page"], body["per_page"], body["total_pages"]) == (4, 1, 2, 2)
    assert len(body["users"]) == 2
    second = await listing(client, people["admin"], per_page=2, page=2)
    assert {u["email"] for u in body["users"]}.isdisjoint({u["email"] for u in second["users"]})
    assert "hashed_password" not in body["users"][0]


@pytest.mark.parametrize(
    "params, emails",
    [
        ({"role": "barber"}, ["bruno@teste.com"]),
        ({"is_active": False}, ["caio@teste.com"]),
        ({"q": "lima"}, ["ana@teste.com"]),
        ({"q": "BRUNO@"}, ["bruno@teste.com"]),
        ({"role": "client", "is_active": True}, ["ana@teste.com"]),
    ],
)
async def test_admin_filters_users(client, people, params, emails):
    body = await listing(client, people["admin"], **params)
    assert sorted(u["email"] for u in body["users"]) == emails
    assert body["total"] == len(emails)


@pytest.mark.parametrize("params", [{"page": 0}, {"per_page": 0}, {"per_page": 101}, {"role": "dono"}])
async def test_invalid_listing_gets_422(client, people, params):
    response = await client.get(f"{URL}/users", params=params, headers=auth(people["admin"]))
    assert response.status_code == 422


async def test_admin_sees_one_user(client, people):
    response = await client.get(f"{URL}/users/{people['ana'].id}", headers=auth(people["admin"]))
    assert response.status_code == 200
    assert response.json()["full_name"] == "Ana Lima"
    unknown = await client.get(f"{URL}/users/{uuid.uuid4()}", headers=auth(people["admin"]))
    assert (unknown.status_code, unknown.json()["detail"]) == (404, "Usuário não encontrado.")


async def test_admin_promotes_a_client_to_barber(client, sessionmaker, people):
    response = await client.put(
        f"{URL}/users/{people['ana'].id}/role", json={"role": "barber"}, headers=auth(people["admin"])
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "barber"
    async with sessionmaker() as db:
        assert (await db.get(User, people["ana"].id)).role == UserRole.BARBER


async def test_invalid_role_gets_422(client, people):
    response = await client.put(
        f"{URL}/users/{people['ana'].id}/role", json={"role": "dono"}, headers=auth(people["admin"])
    )
    assert response.status_code == 422


async def test_admin_cannot_demote_themself(client, sessionmaker, people):
    response = await client.put(
        f"{URL}/users/{people['admin'].id}/role", json={"role": "client"}, headers=auth(people["admin"])
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Você não pode tirar o seu próprio acesso de administrador."
    async with sessionmaker() as db:
        assert (await db.get(User, people["admin"].id)).role == UserRole.ADMIN


async def test_deactivating_blocks_login_and_ends_sessions(client, sessionmaker, admin):
    await user_with_password(sessionmaker, "ana@teste.com")
    first = await login(client, "ana@teste.com")
    assert first.status_code == 200
    async with sessionmaker() as db:
        ana = (await db.execute(select(User).where(User.email == "ana@teste.com"))).scalar_one()

    response = await client.put(f"{URL}/users/{ana.id}/status", json={"is_active": False}, headers=auth(admin))

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert (await login(client, "ana@teste.com")).status_code == 401
    async with sessionmaker() as db:
        sessions = (await db.execute(select(RefreshToken).where(RefreshToken.user_id == ana.id))).scalars().all()
    assert sessions and all(s.revoked_at is not None for s in sessions)

    again = await client.put(f"{URL}/users/{ana.id}/status", json={"is_active": True}, headers=auth(admin))
    assert again.json()["is_active"] is True
    assert (await login(client, "ana@teste.com")).status_code == 200


async def test_admin_cannot_deactivate_themself(client, people):
    response = await client.put(
        f"{URL}/users/{people['admin'].id}/status", json={"is_active": False}, headers=auth(people["admin"])
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Você não pode desativar a sua própria conta."


@pytest.mark.parametrize("path", ["role", "status"])
async def test_changing_unknown_user_gets_404(client, people, path):
    body = {"role": "barber"} if path == "role" else {"is_active": False}
    response = await client.put(f"{URL}/users/{uuid.uuid4()}/{path}", json=body, headers=auth(people["admin"]))
    assert response.status_code == 404


@pytest.mark.parametrize("role", [UserRole.CLIENT, UserRole.BARBER])
async def test_user_admin_routes_are_admin_only(client, sessionmaker, people, role):
    other = await add_user(sessionmaker, f"outro-{role.value}@teste.com", role)
    target = people["ana"].id
    responses = [
        await client.get(f"{URL}/users", headers=auth(other)),
        await client.get(f"{URL}/users/{target}", headers=auth(other)),
        await client.put(f"{URL}/users/{target}/role", json={"role": "admin"}, headers=auth(other)),
        await client.put(f"{URL}/users/{target}/status", json={"is_active": False}, headers=auth(other)),
    ]
    assert [r.status_code for r in responses] == [403] * 4
    async with sessionmaker() as db:
        saved = await db.get(User, target)
    assert (saved.role, saved.is_active) == (UserRole.CLIENT, True)


# ── limite de tentativas de login ───────────────────────


async def test_sixth_failed_login_gets_429_even_with_the_right_password(client, sessionmaker):
    await user_with_password(sessionmaker, "ana@teste.com")
    for _ in range(5):
        assert (await login(client, "ana@teste.com", "errada123")).status_code == 401

    blocked = await login(client, "ana@teste.com")

    assert blocked.status_code == 429
    assert blocked.json()["detail"] == TOO_MANY
    assert 0 < int(blocked.headers["Retry-After"]) <= 15 * 60


async def test_limit_is_per_email(client, sessionmaker):
    await user_with_password(sessionmaker, "ana@teste.com")
    await user_with_password(sessionmaker, "bia@teste.com")
    for _ in range(5):
        await login(client, "ana@teste.com", "errada123")
    assert (await login(client, "bia@teste.com")).status_code == 200


async def test_email_case_counts_as_the_same(client, sessionmaker):
    await user_with_password(sessionmaker, "ana@teste.com")
    for email in ("ana@teste.com", "ANA@teste.com", "Ana@Teste.com", "ana@teste.com", "aNa@teste.com"):
        await login(client, email, "errada123")
    assert (await login(client, "ana@teste.com")).status_code == 429


async def test_successful_login_resets_the_count(client, sessionmaker):
    await user_with_password(sessionmaker, "ana@teste.com")
    for _ in range(4):
        await login(client, "ana@teste.com", "errada123")
    assert (await login(client, "ana@teste.com")).status_code == 200
    for _ in range(4):
        assert (await login(client, "ana@teste.com", "errada123")).status_code == 401
    assert (await login(client, "ana@teste.com")).status_code == 200


async def test_unknown_email_is_limited_too(client, sessionmaker):
    for _ in range(5):
        assert (await login(client, "ninguem@teste.com", "errada123")).status_code == 401
    assert (await login(client, "ninguem@teste.com", "errada123")).status_code == 429

