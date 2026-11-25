"""
Testes de integração das despesas (#3).

Spec: SPEC/2026-11-24-testes-integracao-expenses.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Substituem o tests/test_expenses.py gerado, que não importava a
aplicação.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.auth.models import UserRole
from src.backend.modules.expenses.models import Expense, ExpenseCategory
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/expenses"
NO_CATEGORY = "Categoria informada não existe."
NOT_FOUND = "Despesa não encontrada."


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


async def add_category(client, admin, name):
    response = await client.post(f"{URL}/categories", json={"name": name}, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


async def add_expense(client, admin, description="Conta de luz", amount="180.00", day="2026-11-10", **extra):
    body = {"description": description, "amount": amount, "payment_date": day, **extra}
    response = await client.post(URL, json=body, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


async def expense_in_db(maker, expense_id):
    async with maker() as db:
        return await db.get(Expense, uuid.UUID(str(expense_id)))


async def listed(client, admin, **params):
    response = await client.get(URL, params=params, headers=auth(admin))
    assert response.status_code == 200, response.text
    return [e["description"] for e in response.json()]


# ── categorias ──────────────────────────────────────────


async def test_categories_are_created_and_listed_alphabetically(client, admin):
    rent = await add_category(client, admin, "Aluguel")
    assert rent["name"] == "Aluguel"
    assert rent["id"] and rent["created_at"]
    await add_category(client, admin, "Produtos")
    await add_category(client, admin, "Energia")

    response = await client.get(f"{URL}/categories", headers=auth(admin))
    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["Aluguel", "Energia", "Produtos"]


async def test_no_categories(client, admin):
    response = await client.get(f"{URL}/categories", headers=auth(admin))
    assert response.status_code == 200
    assert response.json() == []


async def test_duplicate_category_gets_400(client, admin, sessionmaker):
    await add_category(client, admin, "Aluguel")
    response = await client.post(f"{URL}/categories", json={"name": "Aluguel"}, headers=auth(admin))
    assert response.status_code == 400
    assert response.json()["detail"] == "Já existe uma categoria chamada 'Aluguel'."
    assert await count(sessionmaker, ExpenseCategory) == 1


@pytest.mark.parametrize("body", [{"name": "x" * 101}, {}, {"name": None}])
async def test_invalid_category_gets_422(client, admin, sessionmaker, body):
    response = await client.post(f"{URL}/categories", json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, ExpenseCategory) == 0


async def test_category_name_limit_is_accepted(client, admin):
    assert len((await add_category(client, admin, "x" * 100))["name"]) == 100


# ── criação de despesa ──────────────────────────────────


async def test_create_expense_with_category(client, admin, sessionmaker):
    rent = await add_category(client, admin, "Aluguel")
    body = await add_expense(
        client, admin, "Aluguel de novembro", "2500.5", "2026-11-05", category_id=rent["id"], is_recurring=True
    )
    assert body["description"] == "Aluguel de novembro"
    assert Decimal(body["amount"]) == Decimal("2500.50")
    assert body["payment_date"] == "2026-11-05"
    assert body["is_recurring"] is True
    assert body["category_id"] == rent["id"]
    assert body["category"] == rent
    assert body["created_at"] and body["updated_at"]

    saved = await expense_in_db(sessionmaker, body["id"])
    assert Decimal(saved.amount) == Decimal("2500.50")
    assert saved.payment_date == date(2026, 11, 5)
    assert str(saved.category_id) == rent["id"]


async def test_create_expense_without_category(client, admin):
    body = await add_expense(client, admin)
    assert body["category_id"] is None
    assert body["category"] is None
    assert body["is_recurring"] is False


async def test_unknown_category_gets_400_and_nothing_is_saved(client, admin, sessionmaker):
    response = await client.post(
        URL,
        json={"description": "Luz", "amount": 10, "payment_date": "2026-11-10", "category_id": str(uuid.uuid4())},
        headers=auth(admin),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == NO_CATEGORY
    assert await count(sessionmaker, Expense) == 0


@pytest.mark.parametrize(
    "change",
    [
        {"amount": 0},
        {"amount": -5},
        {"description": "x" * 256},
        {"payment_date": "10/11/2026"},
        {"description": None},
        {"amount": None},
        {"payment_date": None},
        {"category_id": "nao-e-uuid"},
    ],
)
async def test_invalid_expense_gets_422(client, admin, sessionmaker, change):
    body = {"description": "Luz", "amount": 10, "payment_date": "2026-11-10"}
    body.update(change)
    body = {k: v for k, v in body.items() if v is not None}
    response = await client.post(URL, json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, Expense) == 0


async def test_description_limit_is_accepted(client, admin):
    assert len((await add_expense(client, admin, "x" * 255))["description"]) == 255


# ── listagem ────────────────────────────────────────────


async def test_list_is_newest_payment_first_with_categories(client, admin):
    rent = await add_category(client, admin, "Aluguel")
    await add_expense(client, admin, "Outubro", day="2026-10-05", category_id=rent["id"])
    await add_expense(client, admin, "Dezembro", day="2026-12-05")
    await add_expense(client, admin, "Novembro", day="2026-11-05", category_id=rent["id"])

    body = (await client.get(URL, headers=auth(admin))).json()
    assert [e["description"] for e in body] == ["Dezembro", "Novembro", "Outubro"]
    assert [e["category"]["name"] if e["category"] else None for e in body] == [None, "Aluguel", "Aluguel"]


@pytest.fixture
def period_days():
    return ["2026-10-31", "2026-11-01", "2026-11-15", "2026-11-30", "2026-12-01"]


async def test_period_filter_includes_both_ends(client, admin, period_days):
    for day in period_days:
        await add_expense(client, admin, day, day=day)
    assert await listed(client, admin, start_date="2026-11-01", end_date="2026-11-30") == [
        "2026-11-30", "2026-11-15", "2026-11-01",
    ]


async def test_start_or_end_alone(client, admin, period_days):
    for day in period_days:
        await add_expense(client, admin, day, day=day)
    assert await listed(client, admin, start_date="2026-11-30") == ["2026-12-01", "2026-11-30"]
    assert await listed(client, admin, end_date="2026-11-01") == ["2026-11-01", "2026-10-31"]


async def test_empty_list_and_empty_period(client, admin):
    assert await listed(client, admin) == []
    await add_expense(client, admin, day="2026-11-10")
    assert await listed(client, admin, start_date="2027-01-01") == []


async def test_invalid_period_gets_422(client, admin):
    response = await client.get(URL, params={"start_date": "novembro"}, headers=auth(admin))
    assert response.status_code == 422


# ── alteração ───────────────────────────────────────────


async def test_update_changes_only_sent_fields(client, admin, sessionmaker):
    rent = await add_category(client, admin, "Aluguel")
    expense = await add_expense(client, admin, "Aluguel", "2500.00", "2026-11-05", category_id=rent["id"])
    response = await client.put(f"{URL}/{expense['id']}", json={"amount": "2600"}, headers=auth(admin))
    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(body["amount"]) == Decimal("2600.00")
    assert (body["description"], body["payment_date"], body["category"]["name"]) == ("Aluguel", "2026-11-05", "Aluguel")
    saved = await expense_in_db(sessionmaker, expense["id"])
    assert (Decimal(saved.amount), saved.description) == (Decimal("2600.00"), "Aluguel")


async def test_update_every_field_and_switch_category(client, admin):
    rent = await add_category(client, admin, "Aluguel")
    power = await add_category(client, admin, "Energia")
    expense = await add_expense(client, admin, category_id=rent["id"])
    changes = {"description": "Luz", "amount": "99.9", "payment_date": "2026-11-20", "is_recurring": True,
               "category_id": power["id"]}
    body = (await client.put(f"{URL}/{expense['id']}", json=changes, headers=auth(admin))).json()
    assert (body["description"], body["payment_date"], body["is_recurring"]) == ("Luz", "2026-11-20", True)
    assert Decimal(body["amount"]) == Decimal("99.90")
    assert (body["category_id"], body["category"]["name"]) == (power["id"], "Energia")


async def test_update_can_remove_the_category(client, admin, sessionmaker):
    rent = await add_category(client, admin, "Aluguel")
    expense = await add_expense(client, admin, category_id=rent["id"])
    body = (await client.put(f"{URL}/{expense['id']}", json={"category_id": None}, headers=auth(admin))).json()
    assert body["category_id"] is None
    assert body["category"] is None
    assert (await expense_in_db(sessionmaker, expense["id"])).category_id is None
    assert await count(sessionmaker, ExpenseCategory) == 1


async def test_update_with_unknown_category_gets_400(client, admin, sessionmaker):
    rent = await add_category(client, admin, "Aluguel")
    expense = await add_expense(client, admin, category_id=rent["id"])
    response = await client.put(
        f"{URL}/{expense['id']}", json={"category_id": str(uuid.uuid4()), "amount": 1}, headers=auth(admin)
    )
    assert response.status_code == 400
    assert response.json()["detail"] == NO_CATEGORY
    saved = await expense_in_db(sessionmaker, expense["id"])
    assert (str(saved.category_id), Decimal(saved.amount)) == (rent["id"], Decimal("180.00"))


async def test_update_unknown_expense_gets_404(client, admin):
    response = await client.put(f"{URL}/{uuid.uuid4()}", json={"amount": 1}, headers=auth(admin))
    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


@pytest.mark.parametrize(
    "body", [{"amount": 0}, {"amount": -1}, {"description": "x" * 256}, {"payment_date": "ontem"}]
)
async def test_invalid_update_gets_422(client, admin, sessionmaker, body):
    expense = await add_expense(client, admin)
    response = await client.put(f"{URL}/{expense['id']}", json=body, headers=auth(admin))
    assert response.status_code == 422
    saved = await expense_in_db(sessionmaker, expense["id"])
    assert (saved.description, Decimal(saved.amount)) == ("Conta de luz", Decimal("180.00"))


# ── exclusão ────────────────────────────────────────────


async def test_delete_removes_only_that_expense(client, admin, sessionmaker):
    rent = await add_category(client, admin, "Aluguel")
    wrong = await add_expense(client, admin, "Duplicada", category_id=rent["id"])
    kept = await add_expense(client, admin, "Certa", category_id=rent["id"])

    response = await client.delete(f"{URL}/{wrong['id']}", headers=auth(admin))
    assert response.status_code == 204
    assert response.content == b""
    assert await expense_in_db(sessionmaker, wrong["id"]) is None
    assert await listed(client, admin) == ["Certa"]
    assert await expense_in_db(sessionmaker, kept["id"]) is not None
    assert await count(sessionmaker, ExpenseCategory) == 1


async def test_delete_twice_or_unknown_gets_404(client, admin):
    expense = await add_expense(client, admin)
    assert (await client.delete(f"{URL}/{expense['id']}", headers=auth(admin))).status_code == 204
    for expense_id in (expense["id"], uuid.uuid4()):
        response = await client.delete(f"{URL}/{expense_id}", headers=auth(admin))
        assert response.status_code == 404
        assert response.json()["detail"] == NOT_FOUND


# ── permissões ──────────────────────────────────────────


@pytest.mark.parametrize("role", [None, UserRole.CLIENT, UserRole.BARBER])
async def test_every_route_is_admin_only(client, admin, sessionmaker, role):
    rent = await add_category(client, admin, "Aluguel")
    expense = await add_expense(client, admin, category_id=rent["id"])
    headers = auth(await add_user(sessionmaker, "outro@teste.com", role)) if role else {}
    requests = [
        ("get", f"{URL}/categories", None),
        ("post", f"{URL}/categories", {"name": "Nova"}),
        ("get", URL, None),
        ("post", URL, {"description": "x", "amount": 1, "payment_date": "2026-11-10"}),
        ("put", f"{URL}/{expense['id']}", {"amount": 1}),
        ("delete", f"{URL}/{expense['id']}", None),
    ]
    for method, url, body in requests:
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        response = await getattr(client, method)(url, **kwargs)
        assert response.status_code == 403, (method, url, response.text)

    assert await count(sessionmaker, ExpenseCategory) == 1
    assert await count(sessionmaker, Expense) == 1
    assert Decimal((await expense_in_db(sessionmaker, expense["id"])).amount) == Decimal("180.00")
