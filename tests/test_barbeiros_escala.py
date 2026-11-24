"""
Escala do barbeiro: almoço dentro do expediente, sem troca de dia, alteração parcial de um dia e
a semana inteira de uma vez (#37).

Spec: SPEC/2026-11-23-barbeiros-admin-escala.md

O barbeiro de teste é cadastrado pela API e recebe a escala padrão: domingo de folga e segunda a
sábado das 9h às 18h, com almoço das 12h às 13h.
"""

import uuid
from datetime import time

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.auth.models import UserRole
from src.backend.modules.barbers.models import WorkSchedule
from tests.agenda_fixtures import needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/barbers"
DAY = {"start_time": "09:00:00", "end_time": "18:00:00", "break_start": "12:00:00", "break_end": "13:00:00"}

END_BEFORE_START = "O horário de término deve ser após o início."
INCOMPLETE_BREAK = "Informe o início e o fim do almoço, ou nenhum dos dois."
BREAK_INVERTED = "O fim do almoço deve ser após o início do almoço."
BREAK_OUTSIDE = "O almoço deve ficar dentro do expediente."
DAY_CHANGED = "Não é possível trocar o dia de um registro da escala."
SEVEN_DAYS = "Envie os 7 dias da semana (0 a 6), um de cada."


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN, full_name="Dono")


@pytest_asyncio.fixture
async def barber_id(sessionmaker, client, admin):
    user = await add_user(sessionmaker, "joao@teste.com", full_name="João")
    response = await client.post(URL, json={"user_id": str(user.id)}, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def week_in_db(maker, barber_id):
    """Escala gravada como {dia: (início, fim, almoço início, almoço fim, trabalha)}."""
    async with maker() as db:
        stmt = select(WorkSchedule).where(WorkSchedule.barber_id == uuid.UUID(barber_id))
        rows = (await db.execute(stmt)).scalars().all()
    return {
        s.day_of_week: (s.start_time, s.end_time, s.break_start, s.break_end, s.is_working)
        for s in rows
    } | {"total": len(rows)}


async def day_id(client, barber_id, day):
    response = await client.get(f"{URL}/{barber_id}/schedule")
    return next(s["id"] for s in response.json() if s["day_of_week"] == day)


def messages(response):
    detail = response.json()["detail"]
    if isinstance(detail, str):
        return [detail]
    return [issue["msg"].removeprefix("Value error, ") for issue in detail]


def week(**changes_by_day):
    """Os 7 dias da escala padrão, com as mudanças pedidas por dia (`d3={...}`)."""
    days = []
    for day in range(7):
        base = {"day_of_week": day, **DAY, "is_working": day != 0}
        days.append({**base, **changes_by_day.get(f"d{day}", {})})
    return days


# ── um dia: validações ──────────────────────────────────


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"start_time": "09:00:00", "end_time": "12:00:00", "break_start": "14:00:00", "break_end": "15:00:00"},
         BREAK_OUTSIDE),
        ({"break_start": "08:00:00", "break_end": "09:30:00"}, BREAK_OUTSIDE),
        ({"break_start": "17:30:00", "break_end": "18:30:00"}, BREAK_OUTSIDE),
        ({"break_start": "12:00:00", "break_end": None}, INCOMPLETE_BREAK),
        ({"break_start": None, "break_end": "13:00:00"}, INCOMPLETE_BREAK),
        ({"break_start": "13:00:00", "break_end": "12:00:00"}, BREAK_INVERTED),
        ({"break_start": "12:00:00", "break_end": "12:00:00"}, BREAK_INVERTED),
        ({"start_time": "18:00:00", "end_time": "09:00:00"}, END_BEFORE_START),
        ({"day_of_week": 3}, DAY_CHANGED),
    ],
    ids=["almoco-depois-do-expediente", "almoco-antes-da-abertura", "almoco-passa-do-fim", "sem-fim-do-almoco",
         "sem-inicio-do-almoco", "almoco-invertido", "almoco-de-zero-minutos", "fim-antes-do-inicio",
         "troca-de-dia"],
)
async def test_dia_invalido_responde_422_sem_gravar(changes, message, sessionmaker, client, admin, barber_id):
    terca = await day_id(client, barber_id, 2)
    before = await week_in_db(sessionmaker, barber_id)

    response = await client.put(
        f"{URL}/{barber_id}/schedule/{terca}", json={"day_of_week": 2, **DAY, **changes}, headers=auth(admin)
    )

    assert response.status_code == 422, response.text
    assert messages(response) == [message]
    assert await week_in_db(sessionmaker, barber_id) == before


@pytest.mark.parametrize(
    "changes",
    [
        {"break_start": "09:00:00", "break_end": "10:00:00"},
        {"break_start": "17:00:00", "break_end": "18:00:00"},
        {"break_start": None, "break_end": None},
        {"day_of_week": 2},
    ],
    ids=["almoco-no-inicio", "almoco-no-fim", "sem-almoco", "mesmo-dia"],
)
async def test_dia_valido_e_aceito(changes, sessionmaker, client, admin, barber_id):
    terca = await day_id(client, barber_id, 2)

    response = await client.put(
        f"{URL}/{barber_id}/schedule/{terca}", json={"day_of_week": 2, **DAY, **changes}, headers=auth(admin)
    )

    assert response.status_code == 200, response.text
    assert response.json()["day_of_week"] == 2


# ── um dia: alteração parcial ───────────────────────────


async def test_alteracao_parcial_muda_so_o_enviado(sessionmaker, client, admin, barber_id):
    terca = await day_id(client, barber_id, 2)

    response = await client.put(
        f"{URL}/{barber_id}/schedule/{terca}", json={"end_time": "20:00:00"}, headers=auth(admin)
    )

    assert response.status_code == 200, response.text
    stored = await week_in_db(sessionmaker, barber_id)
    assert stored[2] == (time(9), time(20), time(12), time(13), True)
    assert stored[3] == (time(9), time(18), time(12), time(13), True)


async def test_folga_sem_mandar_os_horarios(sessionmaker, client, admin, barber_id):
    sabado = await day_id(client, barber_id, 6)

    response = await client.put(
        f"{URL}/{barber_id}/schedule/{sabado}", json={"is_working": False}, headers=auth(admin)
    )

    assert response.status_code == 200, response.text
    assert (await week_in_db(sessionmaker, barber_id))[6][4] is False


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"end_time": "11:00:00"}, BREAK_OUTSIDE),
        ({"start_time": "12:30:00"}, BREAK_OUTSIDE),
        ({"break_end": None}, INCOMPLETE_BREAK),
        ({"break_start": "13:00:00"}, BREAK_INVERTED),
        ({"start_time": "19:00:00"}, END_BEFORE_START),
    ],
    ids=["fim-antes-do-almoco", "abertura-depois-do-almoco", "so-apaga-o-fim", "inicio-no-fim-do-almoco",
         "abertura-depois-do-fim"],
)
async def test_regras_valem_para_o_resultado_da_alteracao_parcial(
    payload, message, sessionmaker, client, admin, barber_id
):
    terca = await day_id(client, barber_id, 2)
    before = await week_in_db(sessionmaker, barber_id)

    response = await client.put(f"{URL}/{barber_id}/schedule/{terca}", json=payload, headers=auth(admin))

    assert response.status_code == 422, response.text
    assert messages(response) == [message]
    assert await week_in_db(sessionmaker, barber_id) == before


async def test_null_em_horario_do_expediente_responde_422(sessionmaker, client, admin, barber_id):
    terca = await day_id(client, barber_id, 2)

    for field in ("start_time", "end_time", "is_working"):
        response = await client.put(f"{URL}/{barber_id}/schedule/{terca}", json={field: None}, headers=auth(admin))
        assert response.status_code == 422, field


# ── semana inteira ──────────────────────────────────────


async def test_semana_inteira_grava_os_sete_dias(sessionmaker, client, admin, barber_id):
    payload = week(
        d0={"is_working": True, "start_time": "10:00:00", "end_time": "14:00:00", "break_start": None, "break_end": None},
        d3={"end_time": "20:00:00"},
        d6={"is_working": False},
    )

    response = await client.put(f"{URL}/{barber_id}/schedule", json=list(reversed(payload)), headers=auth(admin))

    assert response.status_code == 200, response.text
    assert [d["day_of_week"] for d in response.json()] == list(range(7))
    stored = await week_in_db(sessionmaker, barber_id)
    assert stored["total"] == 7
    assert stored[0] == (time(10), time(14), None, None, True)
    assert stored[3] == (time(9), time(20), time(12), time(13), True)
    assert stored[6][4] is False
    assert stored[1] == (time(9), time(18), time(12), time(13), True)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (week()[:6], SEVEN_DAYS),
        (week()[:6] + [{**week()[0]}], SEVEN_DAYS),
        (week() + [week()[1]], SEVEN_DAYS),
        ([], SEVEN_DAYS),
        (week(d4={"break_start": "19:00:00", "break_end": "20:00:00"}), BREAK_OUTSIDE),
        (week(d5={"break_end": None}), INCOMPLETE_BREAK),
        (week(d1={"end_time": "08:00:00"}), END_BEFORE_START),
    ],
    ids=["seis-dias", "domingo-repetido", "oito-dias", "vazia", "almoco-fora", "almoco-incompleto",
         "fim-antes-do-inicio"],
)
async def test_semana_invalida_nao_grava_nenhum_dia(payload, message, sessionmaker, client, admin, barber_id):
    before = await week_in_db(sessionmaker, barber_id)

    response = await client.put(f"{URL}/{barber_id}/schedule", json=payload, headers=auth(admin))

    assert response.status_code == 422, response.text
    assert message in messages(response)
    assert await week_in_db(sessionmaker, barber_id) == before


async def test_semana_de_barbeiro_desconhecido_responde_404(sessionmaker, client, admin):
    response = await client.put(f"{URL}/{uuid.uuid4()}/schedule", json=week(), headers=auth(admin))

    assert response.status_code == 404
    assert response.json()["detail"] == "Barbeiro não encontrado."


async def test_rotas_de_escala_sao_so_do_admin(sessionmaker, client, admin, barber_id):
    cliente = await add_user(sessionmaker, "cliente@teste.com")
    barbeiro = await add_user(sessionmaker, "outro@teste.com", UserRole.BARBER)
    terca = await day_id(client, barber_id, 2)
    before = await week_in_db(sessionmaker, barber_id)

    for headers in ({}, auth(cliente), auth(barbeiro)):
        semana = await client.put(f"{URL}/{barber_id}/schedule", json=week(d2={"end_time": "20:00:00"}), headers=headers)
        dia = await client.put(f"{URL}/{barber_id}/schedule/{terca}", json={"end_time": "20:00:00"}, headers=headers)
        assert (semana.status_code, dia.status_code) == (403, 403)
    assert await week_in_db(sessionmaker, barber_id) == before
