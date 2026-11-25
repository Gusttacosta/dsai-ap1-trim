"""
Testes de integração dos agendamentos (#3).

Spec: SPEC/2026-11-24-testes-integracao-appointments.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste e "agora" fixo (ver tests/agenda_fixtures.py). Substituem o
tests/test_appointments.py gerado, que não importava a aplicação. Expediente, fuso, cancelamento,
transições de status e nome do visitante já têm testes próprios e não se repetem aqui.
"""

import uuid
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from src.backend.modules.appointments.models import Appointment, AppointmentItem
from src.backend.modules.appointments.models import AppointmentStatus as S
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber, WorkSchedule
from src.backend.modules.finance.models import BarberCommission, PaymentMethod, Transaction, TransactionType
from src.backend.modules.services.models import BarberServiceAssociation, Service
from tests.agenda_fixtures import brt, count, create_shop, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/appointments"
NOW = brt(2026, 12, 1, 8, 0)  # terça-feira, 08:00 em Brasília
DAY = date(2026, 12, 2)  # quarta-feira (3 no WorkSchedule, que começa no domingo)
WEDNESDAY = 3
INVALID_SERVICES = "Um ou mais serviços são inválidos ou não são prestados por este barbeiro."
CONFLICT = "Conflito de horário. O barbeiro já possui um agendamento nesse período."
DAY_OFF = "O barbeiro não trabalha nesse dia."
ALL_SLOTS_30 = [f"{h:02d}:{m:02d}" for h in range(9, 18) for m in (0, 30)]


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def shop(sessionmaker, set_now):
    """Barbearia de create_shop: cliente, barbeiro de 09:00 às 18:00 todos os dias e um corte
    de 30 min a 40,00."""
    set_now(NOW)
    return await create_shop(sessionmaker)


def at(hour, minute=0, day=DAY):
    return brt(day.year, day.month, day.day, hour, minute)


def local(hour, minute=0, day=DAY):
    """Início sem fuso, como o frontend envia (horário da barbearia)."""
    return f"{day.isoformat()}T{hour:02d}:{minute:02d}:00"


async def add_service(maker, barber_id, *, name, price, duration, is_active=True):
    async with maker() as db:
        service = Service(name=name, price=price, duration_minutes=duration, is_active=is_active)
        db.add(service)
        await db.flush()
        if barber_id is not None:
            db.add(BarberServiceAssociation(barber_id=barber_id, service_id=service.id))
        await db.commit()
        return service.id


async def add_working_barber(maker, email, service_id):
    """Segundo barbeiro, com o mesmo expediente de create_shop e o serviço vinculado."""
    barber = await add_barber(maker, email)
    async with maker() as db:
        db.add(BarberServiceAssociation(barber_id=barber.id, service_id=service_id))
        for day in range(7):
            db.add(WorkSchedule(barber_id=barber.id, day_of_week=day, start_time=time(9), end_time=time(18)))
        await db.commit()
    return barber


async def add_booking(maker, *, client_id, barber_id, start, minutes=30, status=S.CONFIRMED, price=40):
    async with maker() as db:
        appointment = Appointment(
            client_id=client_id,
            barber_id=barber_id,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=minutes),
            status=status,
            total_price=price,
        )
        db.add(appointment)
        await db.commit()
        return appointment.id


async def book(client, user, barber_id, start, service_ids, **extra):
    body = {
        "barber_id": str(barber_id),
        "start_datetime": start,
        "service_ids": [str(s) for s in service_ids],
        **extra,
    }
    return await client.post(URL, json=body, headers=auth(user))


async def book_as_guest(client, barber_id, start, service_ids, name="Ana Souza"):
    body = {
        "barber_id": str(barber_id),
        "start_datetime": start,
        "service_ids": [str(s) for s in service_ids],
        "guest_name": name,
    }
    return await client.post(f"{URL}/guest", json=body)


async def slots(client, barber_id, duration=30, day=DAY):
    params = {"barber_id": str(barber_id), "target_date": day.isoformat(), "duration_minutes": duration}
    response = await client.get(f"{URL}/availability", params=params)
    assert response.status_code == 200, response.text
    return response.json()["available_slots"]


async def set_day_off(maker, barber_id, day_of_week=WEDNESDAY):
    async with maker() as db:
        await db.execute(
            update(WorkSchedule)
            .where(WorkSchedule.barber_id == barber_id, WorkSchedule.day_of_week == day_of_week)
            .values(is_working=False)
        )
        await db.commit()


async def set_commission(maker, barber_id, rate):
    async with maker() as db:
        await db.execute(update(Barber).where(Barber.id == barber_id).values(commission_rate=rate))
        await db.commit()


async def rows(maker, model, *where):
    async with maker() as db:
        return list((await db.execute(select(model).where(*where))).scalars().all())


# ── disponibilidade ─────────────────────────────────────


async def test_free_day_has_every_half_hour_until_the_last_start_that_fits(client, shop):
    assert await slots(client, shop["barber_id"], 30) == ALL_SLOTS_30
    assert await slots(client, shop["barber_id"], 60) == ALL_SLOTS_30[:-1]


async def test_response_echoes_date_and_barber(client, shop):
    params = {"barber_id": str(shop["barber_id"]), "target_date": DAY.isoformat(), "duration_minutes": 30}
    body = (await client.get(f"{URL}/availability", params=params)).json()
    assert body["date"] == "2026-12-02"
    assert body["barber_id"] == str(shop["barber_id"])


@pytest.mark.parametrize("status", [S.PENDING, S.CONFIRMED, S.COMPLETED])
async def test_active_appointment_removes_the_slots_it_overlaps(client, shop, sessionmaker, status):
    await add_booking(
        sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(10), minutes=60,
        status=status,
    )
    free = await slots(client, shop["barber_id"], 30)
    assert "10:00" not in free and "10:30" not in free
    assert "09:30" in free and "11:00" in free
    # Um atendimento de 60 min às 09:30 invadiria o das 10:00.
    assert "09:30" not in await slots(client, shop["barber_id"], 60)


@pytest.mark.parametrize("status", [S.CANCELLED, S.NO_SHOW])
async def test_cancelled_or_no_show_frees_the_slot(client, shop, sessionmaker, status):
    await add_booking(
        sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(10), status=status
    )
    assert await slots(client, shop["barber_id"], 30) == ALL_SLOTS_30


async def test_other_barbers_appointment_does_not_interfere(client, shop, sessionmaker):
    other = await add_working_barber(sessionmaker, "outro@teste.com", shop["service_id"])
    await add_booking(sessionmaker, client_id=shop["client"].id, barber_id=other.id, start=at(10))
    assert await slots(client, shop["barber_id"], 30) == ALL_SLOTS_30
    assert "10:00" not in await slots(client, other.id, 30)


async def test_day_off_has_no_slots(client, shop, sessionmaker):
    await set_day_off(sessionmaker, shop["barber_id"])
    assert await slots(client, shop["barber_id"], 30) == []
    assert await slots(client, shop["barber_id"], 30, day=DAY + timedelta(days=1)) == ALL_SLOTS_30


async def test_unknown_barber_gets_404(client, shop):
    params = {"barber_id": str(uuid.uuid4()), "target_date": DAY.isoformat(), "duration_minutes": 30}
    response = await client.get(f"{URL}/availability", params=params)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "missing_or_bad",
    [
        {"barber_id": None},
        {"target_date": None},
        {"duration_minutes": None},
        {"target_date": "02/12/2026"},
        {"barber_id": "nao-e-uuid"},
        {"duration_minutes": "trinta"},
    ],
)
async def test_missing_or_invalid_query_gets_422(client, shop, missing_or_bad):
    params = {"barber_id": str(shop["barber_id"]), "target_date": DAY.isoformat(), "duration_minutes": 30}
    params.update(missing_or_bad)
    params = {k: v for k, v in params.items() if v is not None}
    response = await client.get(f"{URL}/availability", params=params)
    assert response.status_code == 422


# ── criação pelo cliente ────────────────────────────────


async def test_client_books_and_gets_a_confirmed_appointment(client, shop, sessionmaker):
    response = await book(client, shop["client"], shop["barber_id"], local(10), [shop["service_id"]])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["client_id"] == str(shop["client"].id)
    assert body["barber_id"] == str(shop["barber_id"])
    assert body["notes"] is None
    assert body["created_at"] and body["updated_at"]

    saved = await rows(sessionmaker, Appointment)
    assert [a.id for a in saved] == [uuid.UUID(body["id"])]
    assert saved[0].start_datetime == at(10)
    assert saved[0].end_datetime == at(10, 30)


async def test_two_services_sum_price_and_duration(client, shop, sessionmaker):
    beard = await add_service(sessionmaker, shop["barber_id"], name="Barba", price=Decimal("35.50"), duration=45)
    response = await book(client, shop["client"], shop["barber_id"], local(10), [shop["service_id"], beard])
    assert response.status_code == 201, response.text
    body = response.json()
    assert Decimal(body["total_price"]) == Decimal("75.50")
    saved = (await rows(sessionmaker, Appointment))[0]
    assert saved.end_datetime == at(11, 15)
    assert sorted((i["service_name"], Decimal(i["locked_price"]), i["duration_minutes"]) for i in body["items"]) == [
        ("Barba", Decimal("35.50"), 45),
        ("Corte", Decimal("40.00"), 30),
    ]


async def test_items_are_a_snapshot_of_the_service(client, shop, sessionmaker):
    response = await book(client, shop["client"], shop["barber_id"], local(10), [shop["service_id"]])
    appointment_id = response.json()["id"]

    async with sessionmaker() as db:
        await db.execute(
            update(Service).where(Service.id == shop["service_id"]).values(name="Corte Premium", price=99, duration_minutes=60)
        )
        await db.commit()

    mine = (await client.get(f"{URL}/me", headers=auth(shop["client"]))).json()
    [appointment] = [a for a in mine if a["id"] == appointment_id]
    assert Decimal(appointment["total_price"]) == Decimal("40.00")
    [item] = appointment["items"]
    assert item["service_id"] == str(shop["service_id"])
    assert (item["service_name"], Decimal(item["locked_price"]), item["duration_minutes"]) == (
        "Corte",
        Decimal("40.00"),
        30,
    )


async def test_notes_are_saved(client, shop):
    response = await book(
        client, shop["client"], shop["barber_id"], local(10), [shop["service_id"]], notes="Degradê baixo"
    )
    assert response.status_code == 201
    assert response.json()["notes"] == "Degradê baixo"


async def test_repeated_service_counts_once(client, shop):
    response = await book(
        client, shop["client"], shop["barber_id"], local(10), [shop["service_id"], shop["service_id"]]
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert Decimal(body["total_price"]) == Decimal("40.00")
    assert len(body["items"]) == 1


async def test_new_booking_takes_the_slot_off_availability(client, shop):
    await book(client, shop["client"], shop["barber_id"], local(10), [shop["service_id"]])
    free = await slots(client, shop["barber_id"], 30)
    assert "10:00" not in free
    assert len(free) == len(ALL_SLOTS_30) - 1


# ── serviços inválidos ──────────────────────────────────


@pytest.mark.parametrize("kind", ["desconhecido", "desativado", "de outro barbeiro"])
async def test_invalid_service_gets_400_and_nothing_is_saved(client, shop, sessionmaker, kind):
    if kind == "desconhecido":
        bad = uuid.uuid4()
    elif kind == "desativado":
        bad = await add_service(sessionmaker, shop["barber_id"], name="Antigo", price=10, duration=30, is_active=False)
    else:
        bad = await add_service(sessionmaker, None, name="Só de outro", price=10, duration=30)

    response = await book(client, shop["client"], shop["barber_id"], local(10), [shop["service_id"], bad])
    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_SERVICES
    assert await count(sessionmaker, Appointment) == 0
    assert await count(sessionmaker, AppointmentItem) == 0


async def test_empty_service_list_gets_422(client, shop, sessionmaker):
    response = await book(client, shop["client"], shop["barber_id"], local(10), [])
    assert response.status_code == 422
    assert await count(sessionmaker, Appointment) == 0


@pytest.mark.parametrize("field", ["barber_id", "start_datetime", "service_ids"])
async def test_missing_field_gets_422(client, shop, field):
    body = {
        "barber_id": str(shop["barber_id"]),
        "start_datetime": local(10),
        "service_ids": [str(shop["service_id"])],
    }
    del body[field]
    response = await client.post(URL, json=body, headers=auth(shop["client"]))
    assert response.status_code == 422


# ── conflito e folga ────────────────────────────────────


@pytest.mark.parametrize("status", [S.PENDING, S.CONFIRMED, S.COMPLETED])
@pytest.mark.parametrize("start", [(10, 0), (9, 45), (10, 15)])
async def test_overlap_with_active_appointment_gets_400(client, shop, sessionmaker, status, start):
    await add_booking(
        sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(10), status=status
    )
    response = await book(client, shop["client"], shop["barber_id"], local(*start), [shop["service_id"]])
    assert response.status_code == 400
    assert response.json()["detail"] == CONFLICT
    assert await count(sessionmaker, Appointment) == 1


async def test_longer_booking_that_reaches_the_next_one_conflicts(client, shop, sessionmaker):
    await add_booking(sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(10))
    long = await add_service(sessionmaker, shop["barber_id"], name="Pacote", price=90, duration=90)
    response = await book(client, shop["client"], shop["barber_id"], local(9), [long])
    assert response.status_code == 400
    assert response.json()["detail"] == CONFLICT


async def test_touching_the_previous_appointment_is_accepted(client, shop, sessionmaker):
    await add_booking(sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(10))
    after = await book(client, shop["client"], shop["barber_id"], local(10, 30), [shop["service_id"]])
    before = await book(client, shop["client"], shop["barber_id"], local(9, 30), [shop["service_id"]])
    assert after.status_code == 201, after.text
    assert before.status_code == 201, before.text


@pytest.mark.parametrize("status", [S.CANCELLED, S.NO_SHOW])
async def test_cancelled_or_no_show_does_not_block(client, shop, sessionmaker, status):
    await add_booking(
        sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(10), status=status
    )
    response = await book(client, shop["client"], shop["barber_id"], local(10), [shop["service_id"]])
    assert response.status_code == 201, response.text


async def test_other_barber_at_the_same_time_does_not_block(client, shop, sessionmaker):
    other = await add_working_barber(sessionmaker, "outro@teste.com", shop["service_id"])
    await add_booking(sessionmaker, client_id=shop["client"].id, barber_id=other.id, start=at(10))
    response = await book(client, shop["client"], shop["barber_id"], local(10), [shop["service_id"]])
    assert response.status_code == 201, response.text


async def test_day_off_gets_400(client, shop, sessionmaker):
    await set_day_off(sessionmaker, shop["barber_id"])
    response = await book(client, shop["client"], shop["barber_id"], local(10), [shop["service_id"]])
    assert response.status_code == 400
    assert response.json()["detail"] == DAY_OFF
    assert await count(sessionmaker, Appointment) == 0


# ── visitante ───────────────────────────────────────────


async def test_guest_booking_uses_the_shared_visitor_user(client, shop, sessionmaker):
    """Um único usuário Visitante, inativo, em vez de um guest_<hex> por agendamento (#21)."""
    response = await book_as_guest(client, shop["barber_id"], local(10), [shop["service_id"]], "Ana Souza")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["notes"] == "Visitante: Ana Souza"
    assert body["status"] == "confirmed"

    [guest] = await rows(sessionmaker, User, User.id == uuid.UUID(body["client_id"]))
    assert guest.email == "visitante@trim.local"
    assert guest.full_name == "Visitante"
    assert guest.role == UserRole.CLIENT
    assert guest.is_active is False
    assert not guest.hashed_password.startswith("$2")  # não é um hash bcrypt: nenhuma senha entra
    assert await count(sessionmaker, User) == 3  # cliente, barbeiro e o Visitante


async def test_guest_bookings_share_one_user(client, shop, sessionmaker):
    first = await book_as_guest(client, shop["barber_id"], local(10), [shop["service_id"]], "Ana Souza")
    second = await book_as_guest(client, shop["barber_id"], local(11), [shop["service_id"]], "Bia Lima")
    assert first.status_code == second.status_code == 201
    assert first.json()["client_id"] == second.json()["client_id"]
    assert [first.json()["notes"], second.json()["notes"]] == ["Visitante: Ana Souza", "Visitante: Bia Lima"]
    assert await count(sessionmaker, User) == 3


@pytest.mark.parametrize("reason", ["conflito", "serviço inválido"])
async def test_refused_guest_booking_leaves_no_ghost_user(client, shop, sessionmaker, reason):
    if reason == "conflito":
        await add_booking(sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(10))
        services, detail = [shop["service_id"]], CONFLICT
    else:
        services, detail = [uuid.uuid4()], INVALID_SERVICES
    users_before = await count(sessionmaker, User)

    response = await book_as_guest(client, shop["barber_id"], local(10), services)
    assert response.status_code == 400
    assert response.json()["detail"] == detail
    assert await count(sessionmaker, User) == users_before
    assert await rows(sessionmaker, User, User.email.like("%@trim.local")) == []


# ── agendamentos do cliente e agenda do barbeiro ────────


async def test_client_sees_only_own_appointments_newest_first(client, shop, sessionmaker):
    other = await add_user(sessionmaker, "outra@teste.com")
    early = await book(client, shop["client"], shop["barber_id"], local(9), [shop["service_id"]])
    late = await book(client, shop["client"], shop["barber_id"], local(15), [shop["service_id"]])
    theirs = await book(client, other, shop["barber_id"], local(12), [shop["service_id"]])
    assert early.status_code == late.status_code == theirs.status_code == 201

    mine = (await client.get(f"{URL}/me", headers=auth(shop["client"]))).json()
    assert [a["id"] for a in mine] == [late.json()["id"], early.json()["id"]]
    assert all(a["items"] and a["items"][0]["service_name"] == "Corte" for a in mine)

    their_list = (await client.get(f"{URL}/me", headers=auth(other))).json()
    assert [a["id"] for a in their_list] == [theirs.json()["id"]]


async def test_client_without_appointments_gets_empty_list(client, shop, sessionmaker):
    newcomer = await add_user(sessionmaker, "nova@teste.com")
    response = await client.get(f"{URL}/me", headers=auth(newcomer))
    assert response.status_code == 200
    assert response.json() == []


async def test_barber_sees_only_own_schedule_newest_first(client, shop, sessionmaker):
    other = await add_working_barber(sessionmaker, "outro@teste.com", shop["service_id"])
    first = await add_booking(sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(9))
    last = await add_booking(
        sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(16), status=S.CANCELLED
    )
    await add_booking(sessionmaker, client_id=shop["client"].id, barber_id=other.id, start=at(12))

    response = await client.get(f"{URL}/barber/me", headers=auth(shop["barber_user"]))
    assert response.status_code == 200
    assert [a["id"] for a in response.json()] == [str(last), str(first)]


async def test_barber_with_empty_schedule_gets_empty_list(client, shop):
    response = await client.get(f"{URL}/barber/me", headers=auth(shop["barber_user"]))
    assert response.status_code == 200
    assert response.json() == []


async def test_admin_without_barber_profile_gets_404(client, shop, sessionmaker):
    admin = await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)
    response = await client.get(f"{URL}/barber/me", headers=auth(admin))
    assert response.status_code == 404
    assert response.json()["detail"] == "Perfil de barbeiro não encontrado."


async def test_client_cannot_see_a_barber_schedule(client, shop):
    response = await client.get(f"{URL}/barber/me", headers=auth(shop["client"]))
    assert response.status_code == 403


# ── cobrança ao concluir ────────────────────────────────


async def finish(client, user, appointment_id, status):
    return await client.put(f"{URL}/{appointment_id}/status", json={"status": status.value}, headers=auth(user))


async def test_completing_charges_the_client_and_pays_commission(client, shop, sessionmaker):
    await set_commission(sessionmaker, shop["barber_id"], 30)
    started = NOW - timedelta(minutes=30)
    appointment_id = await add_booking(
        sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=started, price=Decimal("75.00")
    )

    response = await finish(client, shop["barber_user"], appointment_id, S.COMPLETED)
    assert response.status_code == 200, response.text

    [transaction] = await rows(sessionmaker, Transaction)
    assert transaction.type == TransactionType.APPOINTMENT
    assert transaction.reference_id == appointment_id
    assert Decimal(transaction.amount) == Decimal("75.00")
    assert transaction.payment_method == PaymentMethod.CASH
    assert transaction.user_id == shop["client"].id

    [commission] = await rows(sessionmaker, BarberCommission)
    assert commission.barber_id == shop["barber_id"]
    assert commission.transaction_id == transaction.id
    assert Decimal(commission.amount) == Decimal("22.50")
    assert commission.is_paid is False


async def test_commission_uses_each_barbers_rate(client, shop, sessionmaker):
    other = await add_working_barber(sessionmaker, "outro@teste.com", shop["service_id"])
    await set_commission(sessionmaker, other.id, 45)
    started = NOW - timedelta(minutes=30)
    appointment_id = await add_booking(
        sessionmaker, client_id=shop["client"].id, barber_id=other.id, start=started, price=Decimal("40.00")
    )
    admin = await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)

    response = await finish(client, admin, appointment_id, S.COMPLETED)
    assert response.status_code == 200, response.text
    [commission] = await rows(sessionmaker, BarberCommission)
    assert commission.barber_id == other.id
    assert Decimal(commission.amount) == Decimal("18.00")


@pytest.mark.parametrize("final", [S.NO_SHOW, S.CANCELLED])
async def test_no_show_or_cancel_does_not_charge(client, shop, sessionmaker, final):
    start = NOW - timedelta(minutes=30) if final == S.NO_SHOW else NOW + timedelta(hours=3)
    appointment_id = await add_booking(
        sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=start
    )
    response = await finish(client, shop["barber_user"], appointment_id, final)
    assert response.status_code == 200, response.text
    assert await count(sessionmaker, Transaction) == 0
    assert await count(sessionmaker, BarberCommission) == 0


# ── permissões ──────────────────────────────────────────


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", ""),
        ("get", "/me"),
        ("put", "/{id}/cancel"),
        ("get", "/barber/me"),
        ("put", "/{id}/status"),
    ],
)
async def test_protected_routes_need_a_token(client, shop, sessionmaker, method, path):
    appointment_id = await add_booking(
        sessionmaker, client_id=shop["client"].id, barber_id=shop["barber_id"], start=at(10)
    )
    url = URL + path.replace("{id}", str(appointment_id))
    kwargs = {"json": {"status": "cancelled"}} if method == "put" else {}
    if method == "post":
        kwargs = {"json": {"barber_id": str(shop["barber_id"]), "start_datetime": local(11),
                           "service_ids": [str(shop["service_id"])]}}
    response = await getattr(client, method)(url, **kwargs)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"
    assert await count(sessionmaker, Appointment) == 1
    [appointment] = await rows(sessionmaker, Appointment)
    assert appointment.status == S.CONFIRMED


async def test_availability_and_guest_booking_are_public(client, shop):
    assert await slots(client, shop["barber_id"], 30) == ALL_SLOTS_30
    response = await book_as_guest(client, shop["barber_id"], local(10), [shop["service_id"]])
    assert response.status_code == 201
