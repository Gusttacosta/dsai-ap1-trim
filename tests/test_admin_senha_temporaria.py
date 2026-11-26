"""
Senha temporária gerada pelo admin e troca obrigatória no próximo login (#99).

Spec: SPEC/2026-11-25-admin-usuarios.md
"""

import logging
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.auth import security
from src.backend.modules.auth.models import PasswordResetToken, RefreshToken, User, UserRole
from src.backend.modules.auth.schemas import strong_password
from src.backend.modules.auth.service import generate_temporary_password
from tests.agenda_fixtures import needs_db
from tests.api_helpers import add_user, auth

URL = "/api/auth"
PASSWORD = "senhaAntiga123"


def test_generated_passwords_pass_the_strong_password_rule():
    passwords = {generate_temporary_password() for _ in range(200)}
    assert len(passwords) == 200
    for password in passwords:
        assert len(password) == 12 and password.isalnum()
        assert strong_password(password) == password


# ── rota (banco) ────────────────────────────────────────

async def client_with_password(maker, email="ana@teste.com", *, active=True):
    async with maker() as db:
        user = User(
            email=email, hashed_password=security.get_password_hash(PASSWORD),
            full_name="Ana", role=UserRole.CLIENT, is_active=active, email_verified=True,
        )
        db.add(user)
        await db.commit()
        return user


async def login(client, email, password):
    return await client.post(f"{URL}/login", json={"email": email, "password": password})


def generate(client, user_id, who):
    return client.post(f"{URL}/users/{user_id}/temporary-password", headers=auth(who))


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN, full_name="Dono")


@pytest.mark.asyncio
@needs_db
async def test_admin_generates_a_password_that_replaces_the_old_one(client, sessionmaker, admin):
    ana = await client_with_password(sessionmaker)

    response = await generate(client, ana.id, admin)

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    temporary = response.json()["temporary_password"]
    assert len(temporary) == 12
    assert (await login(client, ana.email, PASSWORD)).status_code == 401
    logged = await login(client, ana.email, temporary)
    assert logged.status_code == 200
    assert logged.json()["user"]["must_change_password"] is True


@pytest.mark.asyncio
@needs_db
async def test_generating_ends_sessions_and_pending_reset_links(client, sessionmaker, admin):
    ana = await client_with_password(sessionmaker)
    assert (await login(client, ana.email, PASSWORD)).status_code == 200
    assert (await client.post(f"{URL}/forgot-password", json={"email": ana.email})).status_code == 200

    assert (await generate(client, ana.id, admin)).status_code == 200

    async with sessionmaker() as db:
        sessions = (await db.execute(select(RefreshToken).where(RefreshToken.user_id == ana.id))).scalars().all()
        resets = (await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id == ana.id))).scalars().all()
        stored = await db.get(User, ana.id)
    assert sessions and all(s.revoked_at is not None for s in sessions)
    assert resets and all(r.is_used for r in resets)
    assert stored.must_change_password is True


@pytest.mark.asyncio
@needs_db
async def test_password_never_reaches_the_log(client, sessionmaker, admin, caplog):
    ana = await client_with_password(sessionmaker)
    caplog.set_level(logging.DEBUG)

    temporary = (await generate(client, ana.id, admin)).json()["temporary_password"]
    assert (await login(client, ana.email, temporary)).status_code == 200

    assert caplog.records, "o teste precisa capturar algum registro para valer"
    assert temporary not in caplog.text
    assert all(temporary not in str(record.args) for record in caplog.records)


@pytest.mark.asyncio
@needs_db
@pytest.mark.parametrize("role", [UserRole.CLIENT, UserRole.BARBER])
async def test_only_the_admin_generates(client, sessionmaker, role):
    ana = await client_with_password(sessionmaker)
    someone = await add_user(sessionmaker, "outro@teste.com", role)

    response = await generate(client, ana.id, someone)

    assert response.status_code == 403
    assert (await login(client, ana.email, PASSWORD)).status_code == 200


@pytest.mark.asyncio
@needs_db
async def test_without_token_gets_403(client, sessionmaker):
    ana = await client_with_password(sessionmaker)
    assert (await client.post(f"{URL}/users/{ana.id}/temporary-password")).status_code == 403


@pytest.mark.asyncio
@needs_db
async def test_unknown_user_gets_404(client, admin):
    response = await generate(client, uuid.uuid4(), admin)
    assert response.status_code == 404
    assert response.json()["detail"] == "Usuário não encontrado."


@pytest.mark.asyncio
@needs_db
async def test_admin_cannot_generate_for_themself(client, sessionmaker, admin):
    response = await generate(client, admin.id, admin)

    assert response.status_code == 400
    assert response.json()["detail"] == "Você não pode gerar uma senha temporária para a sua própria conta."
    async with sessionmaker() as db:
        assert (await db.get(User, admin.id)).must_change_password is False


@pytest.mark.asyncio
@needs_db
async def test_inactive_account_is_refused(client, sessionmaker, admin):
    ana = await client_with_password(sessionmaker, active=False)

    response = await generate(client, ana.id, admin)

    assert response.status_code == 400
    assert response.json()["detail"] == "Ative a conta antes de gerar uma senha temporária."
    async with sessionmaker() as db:
        stored = await db.get(User, ana.id)
    assert stored.must_change_password is False
    assert security.verify_password(PASSWORD, stored.hashed_password)
