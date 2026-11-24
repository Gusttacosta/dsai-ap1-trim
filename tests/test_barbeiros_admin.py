"""
Barbeiros: alteração pelo admin, listagem do admin, bio sem comissão, serviços nos detalhes e
agendamento só com barbeiro ativo (#37 e item 5 da #39).

Spec: SPEC/2026-11-23-barbeiros-admin-escala.md

A escala está em tests/test_barbeiros_escala.py.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.config import settings
from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber
from src.backend.modules.services.models import BarberServiceAssociation, Service
from tests.agenda_fixtures import add_appointment, brt, count, create_shop, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/barbers"
FUTURE = datetime(2099, 1, 5, 13, 0, tzinfo=timezone.utc)
PAST = datetime(2000, 1, 5, 13, 0, tzinfo=timezone.utc)
UNAVAILABLE = "Barbeiro indisponível para agendamento."


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN, full_name="Dono")


async def barber_in_db(maker, barber_id):
    async with maker() as db:
        return await db.get(Barber, uuid.UUID(str(barber_id)))


async def put_barber(client, admin, barber_id, payload):
    return await client.put(f"{URL}/{barber_id}", json=payload, headers=auth(admin))


async def barber_user(maker, barber):
    async with maker() as db:
        return await db.get(User, barber.user_id)


# ── PUT /{id} pelo admin ────────────────────────────────


async def test_admin_altera_comissao_bio_e_instagram(sessionmaker, client, admin):
    barber = await add_barber(sessionmaker, "joao@teste.com", full_name="João", commission_rate=50)

    response = await put_barber(
        client, admin, barber.id,
        {"commission_rate": 35.5, "bio": "Degradê", "instagram_url": "https://instagram.com/joao"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(str(body["commission_rate"])) == Decimal("35.5")
    assert body["bio"] == "Degradê"
    assert body["instagram_url"] == "https://instagram.com/joao"
    assert body["full_name"] == "João"
    assert body["email"] == "joao@teste.com"
    stored = await barber_in_db(sessionmaker, barber.id)
    assert stored.commission_rate == Decimal("35.50")
    assert stored.bio == "Degradê"


@pytest.mark.parametrize("commission", [0, 100])
async def test_admin_aceita_comissao_nos_limites(commission, sessionmaker, client, admin):
    barber = await add_barber(sessionmaker, "joao@teste.com")

    response = await put_barber(client, admin, barber.id, {"commission_rate": commission})

    assert response.status_code == 200, response.text
    assert (await barber_in_db(sessionmaker, barber.id)).commission_rate == Decimal(commission)


@pytest.mark.parametrize(
    "payload",
    [
        {"commission_rate": -1},
        {"commission_rate": 100.01},
        {"commission_rate": None},
        {"is_active": None},
        {"bio": "x" * 501},
        {"instagram_url": "nao-e-url"},
        {"comission_rate": 10},
    ],
    ids=["comissao-negativa", "comissao-acima-de-100", "comissao-null", "is-active-null", "bio-501",
         "instagram-invalido", "campo-desconhecido"],
)
async def test_alteracao_invalida_responde_422_sem_mudar(payload, sessionmaker, client, admin):
    barber = await add_barber(sessionmaker, "joao@teste.com", commission_rate=40)

    response = await put_barber(client, admin, barber.id, payload)

    assert response.status_code == 422
    stored = await barber_in_db(sessionmaker, barber.id)
    assert stored.commission_rate == Decimal("40.00")
    assert stored.is_active is True


async def test_null_apaga_bio_e_instagram_e_campo_nao_enviado_fica(sessionmaker, client, admin):
    barber = await add_barber(sessionmaker, "joao@teste.com", commission_rate=40)
    await put_barber(client, admin, barber.id, {"bio": "Antiga", "instagram_url": "https://instagram.com/joao"})

    response = await put_barber(client, admin, barber.id, {"bio": None, "instagram_url": None})

    assert response.status_code == 200, response.text
    stored = await barber_in_db(sessionmaker, barber.id)
    assert (stored.bio, stored.instagram_url) == (None, None)
    assert stored.commission_rate == Decimal("40.00")


async def test_admin_desativa_e_reativa(sessionmaker, client, admin):
    barber = await add_barber(sessionmaker, "joao@teste.com")

    off = await put_barber(client, admin, barber.id, {"is_active": False})

    assert off.status_code == 200, off.text
    assert off.json()["is_active"] is False
    assert (await client.get(f"{URL}/{barber.id}")).status_code == 404
    assert (await client.get(URL)).json() == []

    on = await put_barber(client, admin, barber.id, {"is_active": True})

    assert on.status_code == 200, on.text
    assert (await client.get(f"{URL}/{barber.id}")).status_code == 200
    assert [b["id"] for b in (await client.get(URL)).json()] == [str(barber.id)]


@pytest.mark.parametrize("status", [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
async def test_desativacao_com_agendamento_futuro_e_recusada(status, sessionmaker, client, admin):
    shop = await create_shop(sessionmaker)
    await add_appointment(sessionmaker, shop, start=FUTURE, status=status)
    await add_appointment(sessionmaker, shop, start=FUTURE + timedelta(days=1), status=status)

    response = await put_barber(client, admin, shop["barber_id"], {"is_active": False})

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "O barbeiro tem 2 agendamento(s) futuro(s). Cancele ou remaneje antes de desativá-lo."
    )
    assert (await barber_in_db(sessionmaker, shop["barber_id"])).is_active is True


async def test_desativacao_recusada_nao_grava_os_outros_campos(sessionmaker, client, admin):
    shop = await create_shop(sessionmaker)
    await add_appointment(sessionmaker, shop, start=FUTURE)

    response = await put_barber(client, admin, shop["barber_id"], {"is_active": False, "commission_rate": 10})

    assert response.status_code == 400
    assert (await barber_in_db(sessionmaker, shop["barber_id"])).commission_rate == Decimal("50.00")


async def test_agendamentos_passados_ou_encerrados_nao_impedem_a_desativacao(sessionmaker, client, admin):
    shop = await create_shop(sessionmaker)
    await add_appointment(sessionmaker, shop, start=PAST, status=AppointmentStatus.CONFIRMED)
    for status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW):
        await add_appointment(sessionmaker, shop, start=FUTURE, status=status)
    other = await add_barber(sessionmaker, "outro@teste.com")
    await add_appointment(sessionmaker, shop, start=FUTURE, barber_id=other.id)

    response = await put_barber(client, admin, shop["barber_id"], {"is_active": False})

    assert response.status_code == 200, response.text
    assert (await barber_in_db(sessionmaker, shop["barber_id"])).is_active is False


async def test_reativacao_nao_confere_agendamentos(sessionmaker, client, admin):
    shop = await create_shop(sessionmaker)
    async with sessionmaker() as db:
        (await db.get(Barber, shop["barber_id"])).is_active = False
        await db.commit()
    await add_appointment(sessionmaker, shop, start=FUTURE)

    response = await put_barber(client, admin, shop["barber_id"], {"is_active": True})

    assert response.status_code == 200, response.text


async def test_barbeiro_desconhecido_responde_404(sessionmaker, client, admin):
    response = await put_barber(client, admin, uuid.uuid4(), {"commission_rate": 10})

    assert response.status_code == 404
    assert response.json()["detail"] == "Barbeiro não encontrado."


# ── GET /admin ──────────────────────────────────────────


async def test_listagem_do_admin_traz_todos_em_ordem_com_comissao(sessionmaker, client, admin):
    await add_barber(sessionmaker, "pedro@teste.com", full_name="Pedro", commission_rate=30)
    await add_barber(sessionmaker, "ana@teste.com", full_name="ana", is_active=False)
    await add_barber(sessionmaker, "bruno@teste.com", full_name="Bruno", user_active=False)

    response = await client.get(f"{URL}/admin", headers=auth(admin))

    assert response.status_code == 200, response.text
    body = response.json()
    assert [(b["full_name"], b["is_active"], b["user_is_active"]) for b in body] == [
        ("ana", False, True),
        ("Bruno", True, False),
        ("Pedro", True, True),
    ]
    assert Decimal(str(body[2]["commission_rate"])) == Decimal("30")
    assert body[2]["email"] == "pedro@teste.com"


async def test_rotas_do_admin_recusam_os_outros(sessionmaker, client, admin):
    barber = await add_barber(sessionmaker, "joao@teste.com")
    cliente = await add_user(sessionmaker, "cliente@teste.com")
    barbeiro = await barber_user(sessionmaker, barber)

    for headers in ({}, auth(cliente), auth(barbeiro)):
        assert (await client.get(f"{URL}/admin", headers=headers)).status_code == 403
        put = await client.put(f"{URL}/{barber.id}", json={"commission_rate": 90}, headers=headers)
        assert put.status_code == 403
    assert (await barber_in_db(sessionmaker, barber.id)).commission_rate == Decimal("50.00")


# ── PUT /me/bio ─────────────────────────────────────────


async def test_bio_do_barbeiro_nao_mostra_a_comissao(sessionmaker, client, admin):
    barber = await add_barber(sessionmaker, "joao@teste.com", commission_rate=40)
    barbeiro = await barber_user(sessionmaker, barber)

    response = await client.put(f"{URL}/me/bio", json={"bio": "Nova"}, headers=auth(barbeiro))

    assert response.status_code == 200, response.text
    assert "commission_rate" not in response.json()
    assert response.json()["bio"] == "Nova"
    assert response.json()["is_active"] is True


async def test_barbeiro_apaga_a_bio_e_o_instagram_com_null(sessionmaker, client, admin):
    barber = await add_barber(sessionmaker, "joao@teste.com")
    barbeiro = await barber_user(sessionmaker, barber)
    await client.put(
        f"{URL}/me/bio", json={"bio": "Antiga", "instagram_url": "https://instagram.com/joao"}, headers=auth(barbeiro)
    )

    response = await client.put(f"{URL}/me/bio", json={"bio": None}, headers=auth(barbeiro))

    assert response.status_code == 200, response.text
    stored = await barber_in_db(sessionmaker, barber.id)
    assert stored.bio is None
    assert stored.instagram_url == "https://instagram.com/joao"

    await client.put(f"{URL}/me/bio", json={"instagram_url": None}, headers=auth(barbeiro))
    assert (await barber_in_db(sessionmaker, barber.id)).instagram_url is None


# ── GET /{id} com os serviços ───────────────────────────


async def add_service(maker, name, *, barber_id=None, is_active=True, price=30, minutes=30):
    async with maker() as db:
        service = Service(name=name, price=price, duration_minutes=minutes, is_active=is_active)
        db.add(service)
        await db.flush()
        if barber_id:
            db.add(BarberServiceAssociation(barber_id=barber_id, service_id=service.id))
        await db.commit()
        return service


async def test_detalhes_trazem_os_servicos_ativos_do_barbeiro(sessionmaker, client):
    barber = await add_barber(sessionmaker, "joao@teste.com")
    other = await add_barber(sessionmaker, "pedro@teste.com")
    barba = await add_service(sessionmaker, "barba", barber_id=barber.id, price=25, minutes=20)
    corte = await add_service(sessionmaker, "Corte", barber_id=barber.id, price=40)
    await add_service(sessionmaker, "Pigmentação", barber_id=barber.id, is_active=False)
    await add_service(sessionmaker, "Hidratação", barber_id=other.id)
    await add_service(sessionmaker, "Sobrancelha")

    response = await client.get(f"{URL}/{barber.id}")

    assert response.status_code == 200, response.text
    services = response.json()["services"]
    assert [s["name"] for s in services] == ["barba", "Corte"]
    assert services[0]["id"] == str(barba.id)
    assert Decimal(str(services[0]["price"])) == Decimal("25")
    assert services[0]["duration_minutes"] == 20
    assert services[1]["id"] == str(corte.id)
    assert "commission_rate" not in response.json()


async def test_detalhes_sem_servicos_trazem_lista_vazia(sessionmaker, client):
    barber = await add_barber(sessionmaker, "joao@teste.com")

    response = await client.get(f"{URL}/{barber.id}")

    assert response.json()["services"] == []


# ── agendamento com barbeiro desativado ─────────────────


@pytest.fixture
def agenda(monkeypatch, set_now):
    monkeypatch.setattr(settings, "shop_timezone", "America/Sao_Paulo", raising=False)
    monkeypatch.setattr(settings, "booking_min_lead_minutes", 0, raising=False)
    monkeypatch.setattr(settings, "booking_max_days_ahead", 30, raising=False)
    set_now(brt(2026, 11, 8, 10, 0))


def booking(shop, **extra):
    return {
        "barber_id": str(shop["barber_id"]),
        "service_ids": [str(shop["service_id"])],
        "start_datetime": "2026-11-09T10:00:00-03:00",
        **extra,
    }


async def deactivate(maker, shop, what):
    async with maker() as db:
        if what == "perfil":
            (await db.get(Barber, shop["barber_id"])).is_active = False
        else:
            (await db.get(User, shop["barber_user"].id)).is_active = False
        await db.commit()


@pytest.mark.parametrize("what", ["perfil", "conta"])
async def test_nao_agenda_com_barbeiro_desativado(what, agenda, sessionmaker, client):
    shop = await create_shop(sessionmaker)
    await deactivate(sessionmaker, shop, what)

    guest = await client.post("/api/appointments/guest", json=booking(shop, guest_name="Ana Souza"))
    logged = await client.post("/api/appointments", json=booking(shop), headers=auth(shop["client"]))

    assert (guest.status_code, guest.json()["detail"]) == (400, UNAVAILABLE)
    assert (logged.status_code, logged.json()["detail"]) == (400, UNAVAILABLE)
    assert await count(sessionmaker, Appointment) == 0
    # O visitante recusado também não deixa usuário para trás.
    async with sessionmaker() as db:
        guests = (await db.execute(select(User).where(User.email.like("guest_%")))).scalars().all()
    assert guests == []


@pytest.mark.parametrize("what", ["perfil", "conta"])
async def test_disponibilidade_de_barbeiro_desativado_responde_404(what, agenda, sessionmaker, client):
    shop = await create_shop(sessionmaker)
    await deactivate(sessionmaker, shop, what)

    response = await client.get(
        "/api/appointments/availability",
        params={"barber_id": str(shop["barber_id"]), "target_date": "2026-11-09", "duration_minutes": 30},
    )

    assert (response.status_code, response.json()["detail"]) == (404, UNAVAILABLE)


async def test_barbeiro_ativo_continua_agendando(agenda, sessionmaker, client):
    shop = await create_shop(sessionmaker)

    response = await client.post("/api/appointments/guest", json=booking(shop, guest_name="Ana Souza"))

    assert response.status_code == 201, response.text
