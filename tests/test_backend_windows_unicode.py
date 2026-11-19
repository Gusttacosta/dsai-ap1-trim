"""
Testes do backend em um console Windows cp1252 (#2).

Spec: SPEC/2026-11-19-backend-windows-unicode.md

Dentro de `windows_console()`, `sys.stdout`, `sys.stderr` e o handler de log do backend escrevem
em fluxos cp1252 com errors="strict", como o console do Windows: um emoji na saída levanta
UnicodeEncodeError.
Os testes de cadastro e de recuperação de senha usam o PostgreSQL de TEST_DATABASE_URL.
"""

import io
import logging
import sys
from contextlib import asynccontextmanager, contextmanager

import pytest
from sqlalchemy import select

from src.backend import main
from src.backend.modules.auth.models import PasswordResetToken, User
from tests.agenda_fixtures import needs_db

PASSWORD = "senhaForte123"


def cp1252_stream():
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict", write_through=True)


def written(stream) -> str:
    return stream.buffer.getvalue().decode("cp1252")


def trim_handlers() -> list[logging.Handler]:
    name = getattr(main, "LOG_HANDLER_NAME", None)
    return [h for h in logging.getLogger("src.backend").handlers if h.get_name() == name]


@contextmanager
def windows_console():
    """Troca a saída do processo e a do log do backend por fluxos cp1252 estritos.

    É usado dentro do corpo do teste, e não como fixture, porque o pytest repõe o próprio
    `sys.stdout` entre o setup das fixtures e a execução do teste.
    """
    console = {"stdout": cp1252_stream(), "stderr": cp1252_stream(), "log": cp1252_stream()}
    saved = sys.stdout, sys.stderr
    previous = [(h, h.setStream(console["log"])) for h in trim_handlers()]
    sys.stdout, sys.stderr = console["stdout"], console["stderr"]
    try:
        yield console
    finally:
        sys.stdout, sys.stderr = saved
        for handler, stream in previous:
            handler.setStream(stream)


class FakeEngine:
    """Substitui o engine do banco: registra as funções passadas a run_sync."""

    def __init__(self):
        self.run_sync_calls = []

    @asynccontextmanager
    async def begin(self):
        engine = self

        class Conn:
            async def run_sync(self, fn):
                engine.run_sync_calls.append(fn)

        yield Conn()


def backend_messages(caplog, logger_name):
    return [r.getMessage() for r in caplog.records if r.name == logger_name]


# ── lifespan ────────────────────────────────────────────


async def run_lifespan():
    async with main.lifespan(main.app):
        pass


@pytest.mark.asyncio
async def test_lifespan_inicia_e_encerra_no_console_cp1252(monkeypatch, caplog):
    fake = FakeEngine()
    monkeypatch.setattr(main, "engine", fake)
    caplog.set_level(logging.INFO, logger="src.backend")

    with windows_console():
        await run_lifespan()

    assert fake.run_sync_calls == [main.Base.metadata.create_all]
    messages = backend_messages(caplog, "src.backend.main")
    assert any("backend iniciando" in m for m in messages)
    assert "Banco de dados pronto." in messages
    assert any("backend encerrando" in m for m in messages)


@pytest.mark.asyncio
async def test_lifespan_so_registra_mensagens_ascii(monkeypatch, caplog):
    monkeypatch.setattr(main, "engine", FakeEngine())
    caplog.set_level(logging.INFO, logger="src.backend")

    with windows_console():
        await run_lifespan()

    messages = backend_messages(caplog, "src.backend.main")
    assert len(messages) == 4
    assert all(m.isascii() for m in messages)


@pytest.mark.asyncio
async def test_lifespan_aparece_no_terminal_no_formato_do_uvicorn(monkeypatch):
    monkeypatch.setattr(main, "engine", FakeEngine())

    with windows_console() as console:
        await run_lifespan()

    lines = written(console["log"]).splitlines()
    assert lines[0].startswith("INFO:     ")
    assert "INFO:     Banco de dados pronto." in lines
    assert any("backend encerrando" in line for line in lines)
    assert written(console["stdout"]) == ""


# ── configuração do logging ─────────────────────────────


def test_logger_do_backend_fica_em_info_com_um_unico_handler():
    main.configure_logging()
    main.configure_logging()

    app_logger = logging.getLogger("src.backend")
    assert app_logger.level == logging.INFO
    named = trim_handlers()
    assert len(named) == 1
    assert isinstance(named[0], logging.StreamHandler)


def test_configuracao_nao_altera_o_logger_raiz():
    root = logging.getLogger()
    before = (root.level, list(root.handlers))

    main.configure_logging()

    assert (root.level, list(root.handlers)) == before


def test_loggers_dos_modulos_herdam_o_nivel_info():
    for name in ("src.backend.main", "src.backend.modules.auth.service"):
        assert logging.getLogger(name).getEffectiveLevel() == logging.INFO


# ── cadastro e recuperação de senha (e-mail falso) ──────

EMAIL = "novo@teste.com"


async def register(client):
    return await client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Cliente Novo"},
    )


async def forgot_password(client, email):
    return await client.post("/api/auth/forgot-password", json={"email": email})


@needs_db
@pytest.mark.asyncio
async def test_cadastro_responde_201_no_console_cp1252(sessionmaker, client):
    with windows_console():
        response = await register(client)

    assert response.status_code == 201, response.text
    assert response.json()["user"]["email"] == EMAIL
    async with sessionmaker() as db:
        user = (await db.execute(select(User).where(User.email == EMAIL))).scalar_one()
    assert user.full_name == "Cliente Novo"


@needs_db
@pytest.mark.asyncio
async def test_cadastro_registra_token_de_verificacao_em_ascii(sessionmaker, client, caplog):
    caplog.set_level(logging.INFO, logger="src.backend")

    with windows_console() as console:
        await register(client)

    (message,) = backend_messages(caplog, "src.backend.modules.auth.service")
    assert message.isascii()
    assert f"[MOCK EMAIL] Para verificar o email de {EMAIL}, use o token: " in message
    assert "[MOCK EMAIL]" in written(console["log"])


@needs_db
@pytest.mark.asyncio
async def test_recuperacao_de_senha_responde_200_no_console_cp1252(sessionmaker, client, caplog):
    await register(client)
    caplog.set_level(logging.INFO, logger="src.backend")
    caplog.clear()

    with windows_console():
        response = await forgot_password(client, EMAIL)

    assert response.status_code == 200
    async with sessionmaker() as db:
        token = (await db.execute(select(PasswordResetToken))).scalar_one()
    (message,) = backend_messages(caplog, "src.backend.modules.auth.service")
    assert message.isascii()
    assert message == f"[MOCK EMAIL] Link de reset para {EMAIL}: /reset-password?token={token.token}"


@needs_db
@pytest.mark.asyncio
async def test_recuperacao_de_email_desconhecido_nao_registra_nada(sessionmaker, client, caplog):
    caplog.set_level(logging.INFO, logger="src.backend")

    with windows_console():
        response = await forgot_password(client, "ninguem@teste.com")

    assert response.status_code == 200
    assert backend_messages(caplog, "src.backend.modules.auth.service") == []
