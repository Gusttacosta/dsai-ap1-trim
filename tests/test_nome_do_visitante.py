"""
Nome do visitante validado no backend (#22).

Spec: SPEC/2026-11-23-nome-do-visitante.md

O agendamento é sempre o mesmo (segunda 09/11/2026 às 10:00 de Brasília, "agora" fixo no domingo
anterior); só o `guest_name` muda.
"""

import pytest
from sqlalchemy import select

from src.backend.config import settings
from src.backend.main import app
from src.backend.modules.appointments.models import Appointment
from src.backend.modules.auth.models import User
from tests.agenda_fixtures import brt, count, create_shop, needs_db

pytestmark = [pytest.mark.asyncio, needs_db]

START = "2026-11-09T10:00:00-03:00"
FIRST_AND_LAST = "Informe nome e sobrenome"
CHARACTERS = "Nome deve ter só letras, espaços, apóstrofo, hífen e ponto"
TOO_LONG = "Nome deve ter no máximo 255 caracteres"


@pytest.fixture(autouse=True)
def shop_settings(monkeypatch, set_now):
    monkeypatch.setattr(settings, "shop_timezone", "America/Sao_Paulo", raising=False)
    monkeypatch.setattr(settings, "booking_min_lead_minutes", 0, raising=False)
    monkeypatch.setattr(settings, "booking_max_days_ahead", 30, raising=False)
    set_now(brt(2026, 11, 8, 10, 0))
    yield
    app.dependency_overrides.clear()


async def book(client, shop, guest_name):
    return await client.post(
        "/api/appointments/guest",
        json={
            "barber_id": str(shop["barber_id"]),
            "service_ids": [str(shop["service_id"])],
            "start_datetime": START,
            "guest_name": guest_name,
        },
    )


def messages(response):
    return [issue["msg"].removeprefix("Value error, ") for issue in response.json()["detail"]]


# 255 caracteres exatos: duas palavras separadas por um espaço.
NAME_255 = "A" * 127 + " " + "B" * 127
NAME_256 = "A" * 128 + " " + "B" * 127


@pytest.mark.parametrize(
    ("guest_name", "message"),
    [
        ("", FIRST_AND_LAST),
        ("     ", FIRST_AND_LAST),
        ("sev", FIRST_AND_LAST),
        ("Visitante", FIRST_AND_LAST),
        ("  Severino  ", FIRST_AND_LAST),
        ("Ana S", FIRST_AND_LAST),
        ("A B", FIRST_AND_LAST),
        ("Ana 123", CHARACTERS),
        ("Ana Silva2", CHARACTERS),
        ("Ana Silva²", CHARACTERS),
        ("Ana @Silva", CHARACTERS),
        ("Ana <b>Silva</b>", CHARACTERS),
        ("Ana_Maria Silva", CHARACTERS),
        ("Ana -- Silva", CHARACTERS),
        pytest.param(NAME_256, TOO_LONG, id="256-caracteres"),
        pytest.param("Ana " + "x" * 300, TOO_LONG, id="304-caracteres"),
    ],
)
async def test_nome_invalido_responde_422_e_nao_grava_nada(client, sessionmaker, guest_name, message):
    shop = await create_shop(sessionmaker)
    users_before = await count(sessionmaker, User)

    response = await book(client, shop, guest_name)

    assert response.status_code == 422, response.text
    assert messages(response) == [message]
    assert await count(sessionmaker, User) == users_before
    assert await count(sessionmaker, Appointment) == 0


async def test_sem_guest_name_responde_422(client, sessionmaker):
    shop = await create_shop(sessionmaker)

    response = await client.post(
        "/api/appointments/guest",
        json={"barber_id": str(shop["barber_id"]), "service_ids": [str(shop["service_id"])], "start_datetime": START},
    )

    assert response.status_code == 422
    assert await count(sessionmaker, Appointment) == 0


@pytest.mark.parametrize(
    "guest_name",
    ["Ana Sá", "João da Silva", "Li Wu", "Maria D'Ávila", "Maria-José Souza", "José Souza Jr.", "ÉLIO ÇARDOSO", pytest.param(NAME_255, id="255-caracteres")],
)
async def test_nome_valido_e_aceito(client, sessionmaker, guest_name):
    shop = await create_shop(sessionmaker)

    response = await book(client, shop, guest_name)

    assert response.status_code == 201, response.text
    assert response.json()["notes"] == f"Visitante: {guest_name}"


async def test_nome_gravado_e_o_nome_limpo(client, sessionmaker):
    shop = await create_shop(sessionmaker)

    response = await book(client, shop, "  ana   de \t souza ")

    assert response.status_code == 201, response.text
    assert response.json()["notes"] == "Visitante: ana de souza"
    async with sessionmaker() as db:
        client_id = (await db.execute(select(Appointment.client_id))).scalar_one()
        guest = await db.get(User, client_id)
    assert guest.full_name == "ana de souza"


async def test_limite_conta_depois_da_limpeza(client, sessionmaker):
    """Espaços nas pontas e repetidos não contam nos 255 caracteres."""
    shop = await create_shop(sessionmaker)

    response = await book(client, shop, "   " + NAME_255.replace(" ", "     ") + "   ")

    assert response.status_code == 201, response.text
    assert response.json()["notes"] == f"Visitante: {NAME_255}"
