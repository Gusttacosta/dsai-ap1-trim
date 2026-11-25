"""
Despesas: null no PUT, nomes vazios, valor fora da coluna, período invertido e categorias
editáveis (#65).

Spec: SPEC/2026-11-25-despesas-validacoes.md
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio

from src.backend.modules.auth.models import UserRole
from src.backend.modules.expenses.models import Expense, ExpenseCategory
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/expenses"
EXPENSE = {"description": "Conta de luz", "amount": "100.50", "payment_date": "2026-11-10"}


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


async def post(client, admin, path="", **body):
    return await client.post(f"{URL}{path}", json=body, headers=auth(admin))


async def new_category(client, admin, name="Energia"):
    response = await post(client, admin, "/categories", name=name)
    assert response.status_code == 201, response.text
    return response.json()


async def new_expense(client, admin, **extra):
    response = await post(client, admin, **{**EXPENSE, **extra})
    assert response.status_code == 201, response.text
    return response.json()


async def stored(maker, expense_id):
    async with maker() as db:
        return await db.get(Expense, uuid.UUID(expense_id))


# ── PUT com null ────────────────────────────────────────


@pytest.mark.parametrize("field", ["description", "amount", "payment_date", "is_recurring"])
async def test_put_with_null_in_required_field_gets_422(client, sessionmaker, admin, field):
    expense = await new_expense(client, admin)

    response = await client.put(f"{URL}/{expense['id']}", json={field: None}, headers=auth(admin))

    assert response.status_code == 422
    saved = await stored(sessionmaker, expense["id"])
    assert (saved.description, saved.amount) == ("Conta de luz", Decimal("100.50"))


async def test_put_with_null_category_still_removes_it(client, sessionmaker, admin):
    category = await new_category(client, admin)
    expense = await new_expense(client, admin, category_id=category["id"])

    response = await client.put(f"{URL}/{expense['id']}", json={"category_id": None}, headers=auth(admin))

    assert response.status_code == 200, response.text
    assert response.json()["category_id"] is None


async def test_partial_put_keeps_working(client, sessionmaker, admin):
    expense = await new_expense(client, admin)
    response = await client.put(f"{URL}/{expense['id']}", json={"amount": "80.5"}, headers=auth(admin))
    assert response.status_code == 200, response.text
    assert response.json()["amount"] == "80.50"
    assert response.json()["description"] == "Conta de luz"


# ── textos vazios ───────────────────────────────────────


@pytest.mark.parametrize("name", ["", "   "])
async def test_blank_category_name_gets_422(client, sessionmaker, admin, name):
    assert (await post(client, admin, "/categories", name=name)).status_code == 422
    assert await count(sessionmaker, ExpenseCategory) == 0


async def test_category_name_is_trimmed(client, sessionmaker, admin):
    assert (await new_category(client, admin, "  Aluguel  "))["name"] == "Aluguel"


@pytest.mark.parametrize("description", ["", "   "])
async def test_blank_description_gets_422_on_create_and_update(client, sessionmaker, admin, description):
    assert (await post(client, admin, **{**EXPENSE, "description": description})).status_code == 422
    expense = await new_expense(client, admin)
    response = await client.put(f"{URL}/{expense['id']}", json={"description": description}, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, Expense) == 1


# ── valor ───────────────────────────────────────────────


async def test_create_returns_amount_with_two_places(client, sessionmaker, admin):
    body = await new_expense(client, admin, amount="100.5")
    assert body["amount"] == "100.50"
    listed = (await client.get(URL, headers=auth(admin))).json()
    assert listed[0]["amount"] == body["amount"]


@pytest.mark.parametrize("amount", ["100000000", "1.555"])
async def test_amount_that_does_not_fit_the_column_gets_422(client, sessionmaker, admin, amount):
    """Acima de 99.999.999,99 o banco recusava o valor e a rota respondia 500."""
    assert (await post(client, admin, **{**EXPENSE, "amount": amount})).status_code == 422
    assert await count(sessionmaker, Expense) == 0


async def test_largest_amount_is_accepted(client, sessionmaker, admin):
    assert (await new_expense(client, admin, amount="99999999.99"))["amount"] == "99999999.99"


# ── período ─────────────────────────────────────────────


async def test_inverted_period_gets_422(client, sessionmaker, admin):
    params = {"start_date": "2026-11-30", "end_date": "2026-11-01"}
    response = await client.get(URL, params=params, headers=auth(admin))
    assert response.status_code == 422
    assert response.json()["detail"] == "A data inicial não pode ser depois da data final."


async def test_same_day_period_is_fine(client, sessionmaker, admin):
    await new_expense(client, admin)
    params = {"start_date": "2026-11-10", "end_date": "2026-11-10"}
    response = await client.get(URL, params=params, headers=auth(admin))
    assert response.status_code == 200
    assert len(response.json()) == 1


# ── categorias: renomear e apagar ───────────────────────


async def test_admin_renames_category(client, sessionmaker, admin):
    category = await new_category(client, admin)
    expense = await new_expense(client, admin, category_id=category["id"])

    response = await client.put(f"{URL}/categories/{category['id']}", json={"name": "Luz"}, headers=auth(admin))

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Luz"
    listed = (await client.get(URL, headers=auth(admin))).json()
    assert listed[0]["id"] == expense["id"] and listed[0]["category"]["name"] == "Luz"


async def test_rename_to_existing_name_gets_400(client, sessionmaker, admin):
    await new_category(client, admin, "Aluguel")
    category = await new_category(client, admin, "Energia")

    response = await client.put(
        f"{URL}/categories/{category['id']}", json={"name": "Aluguel"}, headers=auth(admin)
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Já existe uma categoria chamada 'Aluguel'."


async def test_rename_to_its_own_name_is_fine(client, sessionmaker, admin):
    category = await new_category(client, admin, "Energia")
    response = await client.put(
        f"{URL}/categories/{category['id']}", json={"name": "Energia"}, headers=auth(admin)
    )
    assert response.status_code == 200


async def test_rename_with_blank_name_gets_422(client, sessionmaker, admin):
    category = await new_category(client, admin)
    response = await client.put(f"{URL}/categories/{category['id']}", json={"name": " "}, headers=auth(admin))
    assert response.status_code == 422


async def test_delete_category_keeps_its_expenses_without_category(client, sessionmaker, admin):
    category = await new_category(client, admin)
    expense = await new_expense(client, admin, category_id=category["id"])

    response = await client.delete(f"{URL}/categories/{category['id']}", headers=auth(admin))

    assert response.status_code == 204
    assert await count(sessionmaker, ExpenseCategory) == 0
    assert (await stored(sessionmaker, expense["id"])).category_id is None


@pytest.mark.parametrize("method", ["put", "delete"])
async def test_unknown_category_gets_404(client, sessionmaker, admin, method):
    url = f"{URL}/categories/{uuid.uuid4()}"
    if method == "put":
        response = await client.put(url, json={"name": "X"}, headers=auth(admin))
    else:
        response = await client.delete(url, headers=auth(admin))
    assert response.status_code == 404
    assert response.json()["detail"] == "Categoria não encontrada."


@pytest.mark.parametrize("method", ["put", "delete"])
async def test_category_changes_are_admin_only(client, sessionmaker, admin, method):
    category = await new_category(client, admin)
    barber = await add_user(sessionmaker, "barbeiro@teste.com", UserRole.BARBER)
    url = f"{URL}/categories/{category['id']}"
    if method == "put":
        response = await client.put(url, json={"name": "X"}, headers=auth(barber))
    else:
        response = await client.delete(url, headers=auth(barber))
    assert response.status_code == 403
    assert await count(sessionmaker, ExpenseCategory) == 1
