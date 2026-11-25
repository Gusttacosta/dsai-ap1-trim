"""
Testes de integração do financeiro: caixa (PDV) e comissões (#3).

Spec: SPEC/2026-11-24-testes-integracao-finance.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Substituem o tests/test_finance.py gerado, que não importava a aplicação.
A cobrança feita ao marcar `completed` pela rota de status é testada em test_status_agendamento.py
e test_appointments_integracao.py; aqui fica a cobrança pelo caixa.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from src.backend.modules.appointments.models import Appointment
from src.backend.modules.appointments.models import AppointmentStatus as S
from src.backend.modules.auth.models import UserRole
from src.backend.modules.barbers.models import Barber
from src.backend.modules.finance.models import BarberCommission, PaymentMethod, Transaction, TransactionType
from src.backend.modules.products.models import InventoryMovement, MovementType, Product
from tests.agenda_fixtures import brt, count, create_shop, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/finance"
NOW = brt(2026, 12, 1, 14, 0)
ALREADY_CHARGED = "Este agendamento já foi finalizado e cobrado."
NO_PENDING = "Nenhuma comissão pendente encontrada com esses IDs."
TRIM_CLUB_PRODUCT = "Produtos não podem ser pagos com créditos Trim Club nesta versão."
MONEY = [PaymentMethod.CASH, PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD, PaymentMethod.PIX]


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def shop(sessionmaker, set_now):
    """create_shop (cliente, barbeiro com 50% de comissão e um corte) e um admin."""
    set_now(NOW)
    data = await create_shop(sessionmaker)
    data["admin"] = await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)
    return data


async def add_booking(maker, shop, *, price=Decimal("40.00"), status=S.CONFIRMED, barber_id=None, hours_ago=1):
    start = NOW - timedelta(hours=hours_ago)
    async with maker() as db:
        appointment = Appointment(
            client_id=shop["client"].id,
            barber_id=barber_id or shop["barber_id"],
            start_datetime=start,
            end_datetime=start + timedelta(minutes=30),
            status=status,
            total_price=price,
        )
        db.add(appointment)
        await db.commit()
        return appointment.id


async def add_product(maker, *, name="Pomada", price=Decimal("25.00"), stock=5):
    async with maker() as db:
        product = Product(name=name, price=price, stock_quantity=stock)
        db.add(product)
        await db.commit()
        return product.id


async def add_commission(maker, barber_id, client_id, amount, *, is_paid=False):
    """Comissão (com a transação que a gerou) gravada direto no banco, cada uma no seu commit."""
    async with maker() as db:
        transaction = Transaction(
            type=TransactionType.APPOINTMENT,
            reference_id=uuid.uuid4(),
            amount=amount * 2,
            payment_method=PaymentMethod.CASH,
            user_id=client_id,
        )
        db.add(transaction)
        await db.flush()
        commission = BarberCommission(
            barber_id=barber_id, transaction_id=transaction.id, amount=amount, is_paid=is_paid
        )
        db.add(commission)
        await db.commit()
        return commission.id


async def set_commission(maker, barber_id, rate):
    async with maker() as db:
        await db.execute(update(Barber).where(Barber.id == barber_id).values(commission_rate=rate))
        await db.commit()


async def rows(maker, model, *where):
    async with maker() as db:
        return list((await db.execute(select(model).where(*where))).scalars().all())


async def status_of(maker, appointment_id):
    async with maker() as db:
        return (await db.get(Appointment, appointment_id)).status


async def stock_of(maker, product_id):
    async with maker() as db:
        return (await db.get(Product, product_id)).stock_quantity


async def checkout(client, user, appointment_id, method="cash"):
    return await client.post(
        f"{URL}/checkout/appointment/{appointment_id}", json={"payment_method": method}, headers=auth(user)
    )


async def sell(client, user, product_id, quantity=1, method="pix", **extra):
    body = {"product_id": str(product_id), "quantity": quantity, "payment_method": method, **extra}
    return await client.post(f"{URL}/checkout/product", json=body, headers=auth(user))


async def finance_snapshot(maker):
    return (
        await count(maker, Transaction),
        await count(maker, BarberCommission),
        await count(maker, InventoryMovement),
    )


# ── cobrança de agendamento pelo caixa ──────────────────


@pytest.mark.parametrize("method", MONEY)
async def test_checkout_charges_completes_and_pays_commission(client, shop, sessionmaker, method):
    await set_commission(sessionmaker, shop["barber_id"], 30)
    appointment_id = await add_booking(sessionmaker, shop, price=Decimal("75.00"))

    response = await checkout(client, shop["admin"], appointment_id, method.value)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type"] == "appointment"
    assert body["reference_id"] == str(appointment_id)
    assert Decimal(body["amount"]) == Decimal("75.00")
    assert body["payment_method"] == method.value
    assert body["user_id"] == str(shop["client"].id)
    assert body["created_at"]

    assert await status_of(sessionmaker, appointment_id) == S.COMPLETED
    [transaction] = await rows(sessionmaker, Transaction)
    assert str(transaction.id) == body["id"]
    [commission] = await rows(sessionmaker, BarberCommission)
    assert commission.barber_id == shop["barber_id"]
    assert commission.transaction_id == transaction.id
    assert Decimal(commission.amount) == Decimal("22.50")
    assert commission.is_paid is False
    assert commission.paid_at is None


@pytest.mark.parametrize(
    "rate,price,expected",
    [(50, "40.00", "20.00"), (33.33, "40.00", "13.33"), (0, "40.00", "0.00"), (100, "55.90", "55.90")],
)
async def test_commission_follows_the_barbers_rate(client, shop, sessionmaker, rate, price, expected):
    await set_commission(sessionmaker, shop["barber_id"], rate)
    appointment_id = await add_booking(sessionmaker, shop, price=Decimal(price))
    assert (await checkout(client, shop["admin"], appointment_id)).status_code == 201
    [commission] = await rows(sessionmaker, BarberCommission)
    assert Decimal(commission.amount) == Decimal(expected)


async def test_commission_goes_to_the_appointments_barber(client, shop, sessionmaker):
    other = await add_barber(sessionmaker, "outro@teste.com", commission_rate=40)
    appointment_id = await add_booking(sessionmaker, shop, barber_id=other.id)
    assert (await checkout(client, shop["admin"], appointment_id)).status_code == 201
    [commission] = await rows(sessionmaker, BarberCommission)
    assert commission.barber_id == other.id
    assert Decimal(commission.amount) == Decimal("16.00")


async def test_trim_club_credit_records_zero(client, shop, sessionmaker):
    appointment_id = await add_booking(sessionmaker, shop, price=Decimal("75.00"))
    response = await checkout(client, shop["admin"], appointment_id, "trim_club_credit")
    assert response.status_code == 201, response.text
    assert Decimal(response.json()["amount"]) == Decimal("0.00")
    assert response.json()["payment_method"] == "trim_club_credit"
    [commission] = await rows(sessionmaker, BarberCommission)
    assert Decimal(commission.amount) == Decimal("0.00")
    assert await status_of(sessionmaker, appointment_id) == S.COMPLETED


async def test_second_checkout_is_refused(client, shop, sessionmaker):
    appointment_id = await add_booking(sessionmaker, shop)
    assert (await checkout(client, shop["admin"], appointment_id)).status_code == 201
    before = await finance_snapshot(sessionmaker)

    again = await checkout(client, shop["admin"], appointment_id, "pix")
    assert again.status_code == 400
    assert again.json()["detail"] == ALREADY_CHARGED
    assert await finance_snapshot(sessionmaker) == before


async def test_completed_by_the_barber_is_not_charged_again(client, shop, sessionmaker):
    appointment_id = await add_booking(sessionmaker, shop)
    done = await client.put(
        f"/api/appointments/{appointment_id}/status", json={"status": "completed"}, headers=auth(shop["barber_user"])
    )
    assert done.status_code == 200, done.text
    before = await finance_snapshot(sessionmaker)

    response = await checkout(client, shop["admin"], appointment_id)
    assert response.status_code == 400
    assert response.json()["detail"] == ALREADY_CHARGED
    assert await finance_snapshot(sessionmaker) == before


@pytest.mark.parametrize("final", [S.CANCELLED, S.NO_SHOW])
async def test_cancelled_or_no_show_cannot_be_charged(client, shop, sessionmaker, final):
    appointment_id = await add_booking(sessionmaker, shop, status=final)
    response = await checkout(client, shop["admin"], appointment_id)
    assert response.status_code == 400
    assert response.json()["detail"] == f"Não é possível cobrar um agendamento com status {final.value}."
    assert await finance_snapshot(sessionmaker) == (0, 0, 0)
    assert await status_of(sessionmaker, appointment_id) == final


async def test_unknown_appointment_is_refused(client, shop, sessionmaker):
    response = await checkout(client, shop["admin"], uuid.uuid4())
    assert response.status_code in (400, 404)
    assert response.json()["detail"] == "Agendamento não encontrado."
    assert await finance_snapshot(sessionmaker) == (0, 0, 0)


@pytest.mark.parametrize("body", [{"payment_method": "boleto"}, {}])
async def test_invalid_payment_method_gets_422(client, shop, sessionmaker, body):
    appointment_id = await add_booking(sessionmaker, shop)
    response = await client.post(
        f"{URL}/checkout/appointment/{appointment_id}", json=body, headers=auth(shop["admin"])
    )
    assert response.status_code == 422
    assert await status_of(sessionmaker, appointment_id) == S.CONFIRMED


# ── venda de produto no balcão ──────────────────────────


@pytest.mark.parametrize("method", MONEY)
async def test_product_sale_records_revenue_and_lowers_stock(client, shop, sessionmaker, method):
    product_id = await add_product(sessionmaker, price=Decimal("25.50"), stock=5)

    response = await sell(client, shop["admin"], product_id, 3, method.value)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type"] == "product_sale"
    assert body["reference_id"] == str(product_id)
    assert Decimal(body["amount"]) == Decimal("76.50")
    assert body["payment_method"] == method.value
    assert body["user_id"] is None

    assert await stock_of(sessionmaker, product_id) == 2
    [movement] = await rows(sessionmaker, InventoryMovement)
    assert movement.product_id == product_id
    assert movement.quantity == -3
    assert movement.movement_type == MovementType.SALE
    assert movement.user_id == shop["admin"].id
    assert movement.notes == "Venda no balcão"
    assert await count(sessionmaker, BarberCommission) == 0


async def test_product_sale_can_name_the_client(client, shop, sessionmaker):
    product_id = await add_product(sessionmaker)
    response = await sell(client, shop["admin"], product_id, user_id=str(shop["client"].id))
    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == str(shop["client"].id)
    [transaction] = await rows(sessionmaker, Transaction)
    assert transaction.user_id == shop["client"].id


async def test_selling_the_whole_stock_leaves_zero(client, shop, sessionmaker):
    product_id = await add_product(sessionmaker, stock=4)
    assert (await sell(client, shop["admin"], product_id, 4)).status_code == 201
    assert await stock_of(sessionmaker, product_id) == 0

    response = await sell(client, shop["admin"], product_id, 1)
    assert response.status_code == 400
    assert response.json()["detail"] == "Estoque insuficiente. Tentativa de remover 1, mas só existem 0 unidades."


async def test_insufficient_stock_changes_nothing(client, shop, sessionmaker):
    product_id = await add_product(sessionmaker, stock=2)
    response = await sell(client, shop["admin"], product_id, 3)
    assert response.status_code == 400
    assert response.json()["detail"] == "Estoque insuficiente. Tentativa de remover 3, mas só existem 2 unidades."
    assert await stock_of(sessionmaker, product_id) == 2
    assert await finance_snapshot(sessionmaker) == (0, 0, 0)


async def test_trim_club_credit_cannot_buy_products(client, shop, sessionmaker):
    product_id = await add_product(sessionmaker, stock=2)
    response = await sell(client, shop["admin"], product_id, 1, "trim_club_credit")
    assert response.status_code == 400
    assert response.json()["detail"] == TRIM_CLUB_PRODUCT
    assert await stock_of(sessionmaker, product_id) == 2
    assert await finance_snapshot(sessionmaker) == (0, 0, 0)


async def test_unknown_product_gets_400(client, shop, sessionmaker):
    response = await sell(client, shop["admin"], uuid.uuid4())
    assert response.status_code == 400
    assert response.json()["detail"] == "Produto não encontrado."
    assert await finance_snapshot(sessionmaker) == (0, 0, 0)


@pytest.mark.parametrize(
    "change",
    [{"quantity": 0}, {"quantity": -1}, {"quantity": None}, {"product_id": None}, {"payment_method": None},
     {"payment_method": "fiado"}],
)
async def test_invalid_sale_gets_422(client, shop, sessionmaker, change):
    product_id = await add_product(sessionmaker, stock=5)
    body = {"product_id": str(product_id), "quantity": 1, "payment_method": "pix"}
    body.update(change)
    body = {k: v for k, v in body.items() if v is not None}
    response = await client.post(f"{URL}/checkout/product", json=body, headers=auth(shop["admin"]))
    assert response.status_code == 422
    assert await stock_of(sessionmaker, product_id) == 5


# ── extrato ─────────────────────────────────────────────


async def test_statement_lists_every_transaction_newest_first(client, shop, sessionmaker):
    appointment_id = await add_booking(sessionmaker, shop)
    product_id = await add_product(sessionmaker)
    first = (await checkout(client, shop["admin"], appointment_id)).json()
    second = (await sell(client, shop["admin"], product_id)).json()

    response = await client.get(f"{URL}/transactions", headers=auth(shop["admin"]))
    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [second["id"], first["id"]]
    assert [t["type"] for t in response.json()] == ["product_sale", "appointment"]


async def test_empty_statement(client, shop):
    response = await client.get(f"{URL}/transactions", headers=auth(shop["admin"]))
    assert response.status_code == 200
    assert response.json() == []


# ── comissões ───────────────────────────────────────────


@pytest_asyncio.fixture
async def ledger(sessionmaker, shop):
    """Três comissões do barbeiro da barbearia (a do meio já paga) e uma de outro barbeiro."""
    other = await add_barber(sessionmaker, "outro@teste.com")
    client_id = shop["client"].id
    old = await add_commission(sessionmaker, shop["barber_id"], client_id, Decimal("10.00"))
    paid = await add_commission(sessionmaker, shop["barber_id"], client_id, Decimal("15.00"), is_paid=True)
    new = await add_commission(sessionmaker, shop["barber_id"], client_id, Decimal("20.00"))
    theirs = await add_commission(sessionmaker, other.id, client_id, Decimal("30.00"))
    return {"old": old, "paid": paid, "new": new, "theirs": theirs, "other": other}


async def test_admin_sees_pending_commissions_by_default(client, shop, ledger):
    response = await client.get(f"{URL}/commissions/{shop['barber_id']}", headers=auth(shop["admin"]))
    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body] == [str(ledger["new"]), str(ledger["old"])]
    assert [Decimal(c["amount"]) for c in body] == [Decimal("20.00"), Decimal("10.00")]
    assert all(c["is_paid"] is False and c["barber_id"] == str(shop["barber_id"]) for c in body)


async def test_admin_can_see_every_commission(client, shop, ledger):
    response = await client.get(
        f"{URL}/commissions/{shop['barber_id']}", params={"only_pending": "false"}, headers=auth(shop["admin"])
    )
    assert [c["id"] for c in response.json()] == [str(ledger["new"]), str(ledger["paid"]), str(ledger["old"])]


async def test_admin_sees_only_the_requested_barber(client, shop, ledger):
    response = await client.get(f"{URL}/commissions/{ledger['other'].id}", headers=auth(shop["admin"]))
    assert [c["id"] for c in response.json()] == [str(ledger["theirs"])]
    unknown = await client.get(f"{URL}/commissions/{uuid.uuid4()}", headers=auth(shop["admin"]))
    assert unknown.status_code == 200
    assert unknown.json() == []


async def test_barber_sees_own_pending_and_paid_commissions(client, shop, ledger):
    response = await client.get(f"{URL}/commissions/me", headers=auth(shop["barber_user"]))
    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == [str(ledger["new"]), str(ledger["paid"]), str(ledger["old"])]


async def test_admin_without_barber_profile_has_no_own_commissions(client, shop):
    response = await client.get(f"{URL}/commissions/me", headers=auth(shop["admin"]))
    assert response.status_code == 404
    assert response.json()["detail"] == "Perfil de barbeiro não encontrado."


async def test_paying_marks_only_the_chosen_commissions(client, shop, sessionmaker, ledger):
    response = await client.put(
        f"{URL}/commissions/pay",
        json={"barber_id": str(shop["barber_id"]), "commission_ids": [str(ledger["old"])]},
        headers=auth(shop["admin"]),
    )
    assert response.status_code == 200, response.text
    [paid] = response.json()
    assert paid["id"] == str(ledger["old"])
    assert paid["is_paid"] is True
    assert paid["paid_at"]

    pending = await rows(sessionmaker, BarberCommission, BarberCommission.is_paid.is_(False))
    assert sorted(str(c.id) for c in pending) == sorted([str(ledger["new"]), str(ledger["theirs"])])
    [old] = await rows(sessionmaker, BarberCommission, BarberCommission.id == ledger["old"])
    assert old.paid_at is not None


async def test_paying_ignores_ids_of_other_barbers_or_unknown(client, shop, sessionmaker, ledger):
    ids = [str(ledger["new"]), str(ledger["theirs"]), str(uuid.uuid4())]
    response = await client.put(
        f"{URL}/commissions/pay", json={"barber_id": str(shop["barber_id"]), "commission_ids": ids},
        headers=auth(shop["admin"]),
    )
    assert response.status_code == 200, response.text
    assert [c["id"] for c in response.json()] == [str(ledger["new"])]
    [theirs] = await rows(sessionmaker, BarberCommission, BarberCommission.id == ledger["theirs"])
    assert theirs.is_paid is False


@pytest.mark.parametrize("which", ["paid", "theirs"])
async def test_paying_nothing_pending_gets_400(client, shop, sessionmaker, ledger, which):
    response = await client.put(
        f"{URL}/commissions/pay",
        json={"barber_id": str(shop["barber_id"]), "commission_ids": [str(ledger[which])]},
        headers=auth(shop["admin"]),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == NO_PENDING
    assert len(await rows(sessionmaker, BarberCommission, BarberCommission.is_paid.is_(True))) == 1


async def test_paying_twice_gets_400(client, shop, ledger):
    body = {"barber_id": str(shop["barber_id"]), "commission_ids": [str(ledger["old"])]}
    assert (await client.put(f"{URL}/commissions/pay", json=body, headers=auth(shop["admin"]))).status_code == 200
    again = await client.put(f"{URL}/commissions/pay", json=body, headers=auth(shop["admin"]))
    assert again.status_code == 400
    assert again.json()["detail"] == NO_PENDING


async def test_empty_payment_batch_gets_422(client, shop, ledger):
    response = await client.put(
        f"{URL}/commissions/pay", json={"barber_id": str(shop["barber_id"]), "commission_ids": []},
        headers=auth(shop["admin"]),
    )
    assert response.status_code == 422


async def test_commission_from_checkout_can_be_paid(client, shop, sessionmaker):
    appointment_id = await add_booking(sessionmaker, shop)
    assert (await checkout(client, shop["admin"], appointment_id)).status_code == 201
    [mine] = (await client.get(f"{URL}/commissions/me", headers=auth(shop["barber_user"]))).json()
    assert Decimal(mine["amount"]) == Decimal("20.00")

    paid = await client.put(
        f"{URL}/commissions/pay", json={"barber_id": str(shop["barber_id"]), "commission_ids": [mine["id"]]},
        headers=auth(shop["admin"]),
    )
    assert paid.status_code == 200
    pending = await client.get(f"{URL}/commissions/{shop['barber_id']}", headers=auth(shop["admin"]))
    assert pending.json() == []


# ── permissões ──────────────────────────────────────────


def admin_requests(appointment_id, product_id, barber_id, commission_id):
    return [
        ("post", f"{URL}/checkout/appointment/{appointment_id}", {"payment_method": "cash"}),
        ("post", f"{URL}/checkout/product", {"product_id": str(product_id), "quantity": 1, "payment_method": "pix"}),
        ("get", f"{URL}/transactions", None),
        ("get", f"{URL}/commissions/{barber_id}", None),
        ("put", f"{URL}/commissions/pay", {"barber_id": str(barber_id), "commission_ids": [str(commission_id)]}),
    ]


async def call(client, method, url, body, headers=None):
    kwargs = {"headers": headers or {}}
    if body is not None:
        kwargs["json"] = body
    return await getattr(client, method)(url, **kwargs)


@pytest.mark.parametrize("who", [None, "client", "barber_user"])
async def test_admin_routes_are_forbidden_to_others(client, shop, sessionmaker, who):
    appointment_id = await add_booking(sessionmaker, shop)
    product_id = await add_product(sessionmaker, stock=5)
    commission_id = await add_commission(sessionmaker, shop["barber_id"], shop["client"].id, Decimal("10.00"))
    before = await finance_snapshot(sessionmaker)
    headers = auth(shop[who]) if who else None

    for method, url, body in admin_requests(appointment_id, product_id, shop["barber_id"], commission_id):
        response = await call(client, method, url, body, headers)
        assert response.status_code == 403, (method, url, response.text)

    assert await finance_snapshot(sessionmaker) == before
    assert await status_of(sessionmaker, appointment_id) == S.CONFIRMED
    assert await stock_of(sessionmaker, product_id) == 5
    [commission] = await rows(sessionmaker, BarberCommission)
    assert commission.is_paid is False


@pytest.mark.parametrize("who", [None, "client"])
async def test_own_commissions_need_barber_or_admin(client, shop, who):
    headers = auth(shop[who]) if who else None
    response = await call(client, "get", f"{URL}/commissions/me", None, headers)
    assert response.status_code == 403
