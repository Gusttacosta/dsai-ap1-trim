"""
Agendamento só dentro do expediente e fora do almoço (#23).

Spec: SPEC/2026-11-22-agendamento-dentro-do-expediente.md

"Agora" fica fixo no domingo 08/11/2026 às 10:00 de Brasília; os agendamentos são para a
segunda 09/11. O barbeiro de teste trabalha das 09:00 às 18:00, todos os dias.
"""

import pytest
from sqlalchemy import func, select

from src.backend.config import settings
from src.backend.main import app
from src.backend.modules.appointments.models import Appointment
from src.backend.modules.auth.dependencies import get_current_user
from src.backend.modules.auth.models import User
from src.backend.modules.services.models import BarberServiceAssociation, Service
from tests.agenda_fixtures import brt, count, create_shop, needs_db

pytestmark = [pytest.mark.asyncio, needs_db]

DAY = "2026-11-09"
LUNCH = ("12:00", "13:00")
OUTSIDE = "Horário fora do expediente do barbeiro nesse dia (09:00 às 18:00)."
IN_LUNCH = "Horário cai no intervalo de almoço do barbeiro (12:00 às 13:00)."


@pytest.fixture(autouse=True)
def shop_settings(monkeypatch, set_now):
    monkeypatch.setattr(settings, "shop_timezone", "America/Sao_Paulo", raising=False)
    monkeypatch.setattr(settings, "booking_min_lead_minutes", 0, raising=False)
    monkeypatch.setattr(settings, "booking_max_days_ahead", 30, raising=False)
    set_now(brt(2026, 11, 8, 10, 0))
    yield
    app.dependency_overrides.clear()


async def add_service(maker, shop, name, minutes):
    """Outro serviço do mesmo barbeiro, para somar durações."""
    async with maker() as db:
        service = Service(name=name, price=20, duration_minutes=minutes)
        db.add(service)
        await db.flush()
        db.add(BarberServiceAssociation(barber_id=shop["barber_id"], service_id=service.id))
        await db.commit()
        return service.id


async def book_as_guest(client, shop, start, service_ids=None):
    return await client.post(
        "/api/appointments/guest",
        json={
            "barber_id": str(shop["barber_id"]),
            "service_ids": [str(s) for s in (service_ids or [shop["service_id"]])],
            "start_datetime": start,
            "guest_name": "Visitante Teste",
        },
    )


async def users(maker):
    async with maker() as db:
        return (await db.execute(select(func.count()).select_from(User))).scalar_one()


async def assert_refused(client, maker, shop, start, message, service_ids=None):
    users_before = await users(maker)

    response = await book_as_guest(client, shop, start, service_ids)

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == message
    assert await count(maker, Appointment) == 0
    assert await users(maker) == users_before


# ── os casos da issue ───────────────────────────────────


async def test_madrugada_e_recusada(client, sessionmaker):
    shop = await create_shop(sessionmaker, lunch=LUNCH)

    await assert_refused(client, sessionmaker, shop, f"{DAY}T03:00:00", OUTSIDE)


async def test_no_meio_do_almoco_e_recusado(client, sessionmaker):
    shop = await create_shop(sessionmaker, lunch=LUNCH)

    await assert_refused(client, sessionmaker, shop, f"{DAY}T12:15:00", IN_LUNCH)


async def test_atendimento_que_passa_do_fim_do_expediente_e_recusado(client, sessionmaker):
    shop = await create_shop(sessionmaker, lunch=LUNCH)

    await assert_refused(client, sessionmaker, shop, f"{DAY}T17:45:00", OUTSIDE)


# ── outros limites ──────────────────────────────────────


async def test_um_minuto_antes_do_inicio_e_recusado(client, sessionmaker):
    shop = await create_shop(sessionmaker)

    await assert_refused(client, sessionmaker, shop, f"{DAY}T08:59:00", OUTSIDE)


async def test_soma_dos_servicos_que_passa_do_fim_e_recusada(client, sessionmaker):
    shop = await create_shop(sessionmaker)
    barba = await add_service(sessionmaker, shop, "Barba", 20)

    # 17:30 + 30 min de corte + 20 min de barba = 18:20
    await assert_refused(client, sessionmaker, shop, f"{DAY}T17:30:00", OUTSIDE, [shop["service_id"], barba])


async def test_atendimento_que_entra_no_almoco_e_recusado(client, sessionmaker):
    shop = await create_shop(sessionmaker, lunch=LUNCH)

    await assert_refused(client, sessionmaker, shop, f"{DAY}T11:45:00", IN_LUNCH)


async def test_atendimento_que_cobre_o_almoco_inteiro_e_recusado(client, sessionmaker):
    shop = await create_shop(sessionmaker, lunch=("12:00", "12:30"))
    longo = await add_service(sessionmaker, shop, "Progressiva", 120)

    await assert_refused(
        client, sessionmaker, shop, f"{DAY}T11:00:00", "Horário cai no intervalo de almoço do barbeiro (12:00 às 12:30).", [longo]
    )


@pytest.mark.parametrize(
    "start",
    ["09:00", "09:15", "11:30", "13:00", "17:30"],
    ids=["abertura", "fora-da-grade", "termina-no-almoco", "fim-do-almoco", "termina-no-fechamento"],
)
async def test_limites_do_expediente_sao_aceitos(client, sessionmaker, start):
    shop = await create_shop(sessionmaker, lunch=LUNCH)

    response = await book_as_guest(client, shop, f"{DAY}T{start}:00")

    assert response.status_code == 201, response.text
    assert await count(sessionmaker, Appointment) == 1


async def test_sem_almoco_o_meio_dia_e_aceito(client, sessionmaker):
    shop = await create_shop(sessionmaker)

    response = await book_as_guest(client, shop, f"{DAY}T12:15:00")

    assert response.status_code == 201, response.text


async def test_expediente_e_conferido_no_fuso_da_barbearia(client, sessionmaker):
    shop = await create_shop(sessionmaker)

    # 20:30 UTC = 17:30 em Brasília (dentro); 11:30 UTC = 08:30 (antes da abertura).
    inside = await book_as_guest(client, shop, f"{DAY}T20:30:00Z")
    outside = await book_as_guest(client, shop, f"{DAY}T11:30:00Z")

    assert inside.status_code == 201, inside.text
    assert outside.status_code == 400
    assert outside.json()["detail"] == OUTSIDE


async def test_horarios_do_expediente_aparecem_na_mensagem(client, sessionmaker):
    shop = await create_shop(sessionmaker, start="10:00", end="16:00")

    await assert_refused(
        client, sessionmaker, shop, f"{DAY}T09:30:00", "Horário fora do expediente do barbeiro nesse dia (10:00 às 16:00)."
    )


# ── cliente logado ──────────────────────────────────────


@pytest.mark.parametrize(("start", "message"), [("03:00", OUTSIDE), ("12:15", IN_LUNCH), ("17:45", OUTSIDE)])
async def test_cliente_logado_tem_as_mesmas_recusas(client, sessionmaker, start, message):
    shop = await create_shop(sessionmaker, lunch=LUNCH)
    app.dependency_overrides[get_current_user] = lambda: shop["client"]

    response = await client.post(
        "/api/appointments",
        json={
            "barber_id": str(shop["barber_id"]),
            "service_ids": [str(shop["service_id"])],
            "start_datetime": f"{DAY}T{start}:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == message
    assert await count(sessionmaker, Appointment) == 0


# ── a disponibilidade não muda ──────────────────────────


async def test_disponibilidade_continua_a_mesma(client, sessionmaker):
    shop = await create_shop(sessionmaker, lunch=LUNCH)

    response = await client.get(
        "/api/appointments/availability",
        params={"barber_id": str(shop["barber_id"]), "target_date": DAY, "duration_minutes": 30},
    )

    slots = response.json()["available_slots"]
    assert slots[0] == "09:00"
    assert slots[-1] == "17:30"
    assert "11:30" in slots and "13:00" in slots
    assert "12:00" not in slots and "12:30" not in slots
    assert len(slots) == 16
