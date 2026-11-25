"""
Produtos: null no PUT, foto longa, SKU vazio, nomes, sinal da movimentação, produto desativado e
reativação (#61).

Spec: SPEC/2026-11-25-produtos-validacoes.md
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio

from src.backend.modules.auth.models import UserRole
from src.backend.modules.products.models import InventoryMovement, Product
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/products"


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


async def create(client, admin, name="Pomada", **extra):
    response = await client.post(URL, json={"name": name, "price": "25.00", **extra}, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


async def put(client, admin, product_id, body):
    return await client.put(f"{URL}/{product_id}", json=body, headers=auth(admin))


async def move(client, admin, product_id, quantity, kind):
    body = {"quantity": quantity, "movement_type": kind}
    return await client.post(f"{URL}/{product_id}/inventory", json=body, headers=auth(admin))


async def saved(maker, product_id):
    async with maker() as db:
        return await db.get(Product, uuid.UUID(product_id))


# ── 1 a 3: erros 500 ────────────────────────────────────


@pytest.mark.parametrize("field", ["name", "price", "is_active"])
async def test_put_with_null_in_required_field_gets_422(client, sessionmaker, admin, field):
    product = await create(client, admin)
    assert (await put(client, admin, product["id"], {field: None})).status_code == 422
    row = await saved(sessionmaker, product["id"])
    assert (row.name, Decimal(row.price), row.is_active) == ("Pomada", Decimal("25.00"), True)


@pytest.mark.parametrize("field", ["description", "sku", "cost_price", "image_url"])
async def test_put_with_null_in_optional_field_clears_it(client, sessionmaker, admin, field):
    product = await create(client, admin, description="d", sku="P-1", cost_price="5", image_url="https://e.com/p.png")
    response = await put(client, admin, product["id"], {field: None})
    assert response.status_code == 200, response.text
    assert getattr(await saved(sessionmaker, product["id"]), field) is None


async def test_image_url_over_500_chars_gets_422(client, sessionmaker, admin):
    long_url = "https://e.com/" + "a" * 487  # 501 caracteres
    response = await client.post(URL, json={"name": "Pomada", "price": 1, "image_url": long_url}, headers=auth(admin))
    assert response.status_code == 422
    product = await create(client, admin)
    assert (await put(client, admin, product["id"], {"image_url": long_url})).status_code == 422
    assert (await create(client, admin, "Cera", image_url=long_url[:500]))["image_url"] == long_url[:500]


@pytest.mark.parametrize("blank", ["", "   "])
async def test_blank_sku_is_no_sku_and_can_repeat(client, sessionmaker, admin, blank):
    first = await create(client, admin, "Pomada", sku=blank)
    second = await create(client, admin, "Cera", sku=blank)
    assert first["sku"] is None and second["sku"] is None
    other = await create(client, admin, "Balm", sku="B-1")
    response = await put(client, admin, other["id"], {"sku": blank})
    assert response.status_code == 200
    assert response.json()["sku"] is None


# ── 4 e 5: nomes ────────────────────────────────────────


@pytest.mark.parametrize("name", ["", "   "])
async def test_blank_name_gets_422(client, sessionmaker, admin, name):
    response = await client.post(URL, json={"name": name, "price": 1}, headers=auth(admin))
    assert response.status_code == 422
    product = await create(client, admin)
    assert (await put(client, admin, product["id"], {"name": name})).status_code == 422
    assert await count(sessionmaker, Product) == 1


async def test_name_is_unique_ignoring_case(client, sessionmaker, admin):
    await create(client, admin, "Pomada")
    response = await client.post(URL, json={"name": "pomada", "price": 1}, headers=auth(admin))
    assert response.status_code == 400
    assert response.json()["detail"] == "Já existe um produto com o nome 'pomada'."
    other = await create(client, admin, "Cera")
    assert (await put(client, admin, other["id"], {"name": "POMADA"})).status_code == 400


async def test_changing_only_the_case_of_its_own_name_is_fine(client, admin):
    product = await create(client, admin, "Pomada")
    response = await put(client, admin, product["id"], {"name": "POMADA"})
    assert response.status_code == 200
    assert response.json()["name"] == "POMADA"


# ── 6: sinal da movimentação ────────────────────────────


@pytest.mark.parametrize(
    "quantity, kind",
    [(0, "restock"), (0, "adjustment"), (-5, "restock"), (5, "sale"), (5, "loss")],
)
async def test_movement_with_wrong_sign_or_zero_gets_422(client, sessionmaker, admin, quantity, kind):
    product = await create(client, admin)
    assert (await move(client, admin, product["id"], 10, "restock")).status_code == 200

    assert (await move(client, admin, product["id"], quantity, kind)).status_code == 422
    assert (await saved(sessionmaker, product["id"])).stock_quantity == 10
    assert await count(sessionmaker, InventoryMovement) == 1


@pytest.mark.parametrize("quantity, stock", [(3, 13), (-3, 7)])
async def test_adjustment_goes_both_ways(client, admin, quantity, stock):
    product = await create(client, admin)
    await move(client, admin, product["id"], 10, "restock")
    response = await move(client, admin, product["id"], quantity, "adjustment")
    assert response.status_code == 200
    assert response.json()["stock_quantity"] == stock


# ── 7: produto desativado ───────────────────────────────


async def deactivated(client, admin, stock=5):
    product = await create(client, admin)
    await move(client, admin, product["id"], stock, "restock")
    assert (await client.delete(f"{URL}/{product['id']}", headers=auth(admin))).status_code == 204
    return product


@pytest.mark.parametrize("quantity, kind", [(-1, "sale"), (3, "restock")])
async def test_deactivated_product_refuses_sale_and_restock(client, sessionmaker, admin, quantity, kind):
    product = await deactivated(client, admin)
    response = await move(client, admin, product["id"], quantity, kind)
    assert response.status_code == 400
    assert response.json()["detail"] == "Produto desativado: só aceita perda ou ajuste de estoque."
    assert (await saved(sessionmaker, product["id"])).stock_quantity == 5


@pytest.mark.parametrize("quantity, kind", [(-5, "loss"), (-5, "adjustment")])
async def test_deactivated_product_can_clear_its_stock(client, admin, quantity, kind):
    product = await deactivated(client, admin)
    response = await move(client, admin, product["id"], quantity, kind)
    assert response.status_code == 200
    assert response.json()["stock_quantity"] == 0


async def test_cashier_cannot_sell_a_deactivated_product(client, sessionmaker, admin):
    product = await deactivated(client, admin)
    body = {"product_id": product["id"], "quantity": 1, "payment_method": "cash"}
    response = await client.post("/api/finance/checkout/product", json=body, headers=auth(admin))
    assert response.status_code == 400
    assert (await saved(sessionmaker, product["id"])).stock_quantity == 5


# ── 8: reativação ───────────────────────────────────────


async def test_put_is_active_reactivates_the_product(client, sessionmaker, admin):
    product = await deactivated(client, admin)

    response = await put(client, admin, product["id"], {"is_active": True})

    assert response.status_code == 200
    assert response.json()["is_active"] is True
    showcase = (await client.get(URL)).json()
    assert [p["id"] for p in showcase] == [product["id"]]
    assert (await move(client, admin, product["id"], -1, "sale")).status_code == 200


async def test_put_is_active_false_also_deactivates(client, sessionmaker, admin):
    product = await create(client, admin)
    assert (await put(client, admin, product["id"], {"is_active": False})).json()["is_active"] is False
    assert (await saved(sessionmaker, product["id"])).is_active is False
