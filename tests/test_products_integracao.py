"""
Testes de integração dos produtos e do estoque (#3).

Spec: SPEC/2026-11-24-testes-integracao-products.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Substituem o tests/test_products.py gerado, que não importava a
aplicação. A venda no balcão, que baixa o estoque pelo ProductService, fica em
test_finance_integracao.py.
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.backend.modules.auth.models import UserRole
from src.backend.modules.products.models import InventoryMovement, MovementType, Product
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/products"
PUBLIC_FIELDS = {"id", "name", "description", "sku", "price", "stock_quantity", "is_active", "image_url"}
ADMIN_FIELDS = PUBLIC_FIELDS | {"cost_price", "created_at", "updated_at"}
UNAVAILABLE = "Produto não encontrado ou indisponível."
NOT_FOUND = "Produto não encontrado."


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


async def create(client, admin, name="Pomada", price="25.00", **extra):
    response = await client.post(URL, json={"name": name, "price": price, **extra}, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


async def move(client, admin, product_id, quantity, kind="restock", notes=None):
    body = {"quantity": quantity, "movement_type": kind}
    if notes is not None:
        body["notes"] = notes
    return await client.post(f"{URL}/{product_id}/inventory", json=body, headers=auth(admin))


async def stocked(client, admin, name, quantity, price="10.00", **extra):
    product = await create(client, admin, name=name, price=price, **extra)
    if quantity:
        assert (await move(client, admin, product["id"], quantity)).status_code == 200
    return product


async def deactivate(client, admin, product_id):
    return await client.delete(f"{URL}/{product_id}", headers=auth(admin))


async def product_in_db(maker, product_id):
    async with maker() as db:
        return await db.get(Product, uuid.UUID(str(product_id)))


async def movements_in_db(maker):
    async with maker() as db:
        return list((await db.execute(select(InventoryMovement))).scalars().all())


async def names(client, url=URL, **params):
    response = await client.get(url, params=params)
    assert response.status_code == 200, response.text
    return [p["name"] for p in response.json()]


# ── vitrine ─────────────────────────────────────────────


async def test_showcase_lists_active_products_in_stock_alphabetically(client, admin):
    await stocked(client, admin, "Óleo", 2)
    await stocked(client, admin, "Cera", 1)
    await stocked(client, admin, "Balm", 0)
    gone = await stocked(client, admin, "Antigo", 3)
    await deactivate(client, admin, gone["id"])

    assert await names(client) == ["Cera", "Óleo"]


async def test_showcase_can_include_out_of_stock(client, admin):
    await stocked(client, admin, "Cera", 1)
    await stocked(client, admin, "Balm", 0)
    gone = await stocked(client, admin, "Antigo", 0)
    await deactivate(client, admin, gone["id"])

    assert await names(client, show_out_of_stock="true") == ["Balm", "Cera"]


async def test_showcase_hides_cost_and_dates(client, admin):
    await stocked(client, admin, "Cera", 1, cost_price="4.00", sku="CER-1", description="Fixação forte")
    [product] = (await client.get(URL)).json()
    assert set(product) == PUBLIC_FIELDS
    assert product["sku"] == "CER-1"
    assert product["description"] == "Fixação forte"
    assert product["stock_quantity"] == 1


async def test_empty_showcase(client, sessionmaker):
    response = await client.get(URL)
    assert response.status_code == 200
    assert response.json() == []


async def test_public_details_show_active_product_even_without_stock(client, admin):
    product = await create(client, admin, "Balm", cost_price="3.00")
    response = await client.get(f"{URL}/{product['id']}")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == PUBLIC_FIELDS
    assert body["name"] == "Balm"
    assert body["stock_quantity"] == 0


async def test_public_details_of_unknown_or_inactive_get_404(client, admin):
    product = await stocked(client, admin, "Cera", 2)
    await deactivate(client, admin, product["id"])

    for product_id in (product["id"], uuid.uuid4()):
        response = await client.get(f"{URL}/{product_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == UNAVAILABLE


# ── listagem do admin ───────────────────────────────────


async def test_admin_sees_every_product_with_cost(client, admin):
    await stocked(client, admin, "Cera", 1, cost_price="4.50")
    await stocked(client, admin, "Balm", 0)
    gone = await stocked(client, admin, "Antigo", 3)
    await deactivate(client, admin, gone["id"])

    response = await client.get(f"{URL}/admin/all", headers=auth(admin))
    assert response.status_code == 200
    body = response.json()
    assert [p["name"] for p in body] == ["Antigo", "Balm", "Cera"]
    assert all(set(p) == ADMIN_FIELDS for p in body)
    assert [p["is_active"] for p in body] == [False, True, True]
    assert [p["stock_quantity"] for p in body] == [3, 0, 1]
    assert Decimal(body[2]["cost_price"]) == Decimal("4.50")
    assert body[1]["cost_price"] is None


# ── criação ─────────────────────────────────────────────


async def test_create_starts_active_with_zero_stock(client, admin, sessionmaker):
    body = await create(
        client, admin, "Pomada Matte", "39.9", description="Efeito seco", sku="POM-01", cost_price="12.345",
        image_url="https://exemplo.com/pomada.png", stock_quantity=50, is_active=False,
    )
    assert body["stock_quantity"] == 0
    assert body["is_active"] is True
    assert Decimal(body["price"]) == Decimal("39.90")
    assert body["description"] == "Efeito seco"
    assert body["sku"] == "POM-01"
    assert body["image_url"] == "https://exemplo.com/pomada.png"
    assert body["created_at"] and body["updated_at"]

    saved = await product_in_db(sessionmaker, body["id"])
    assert saved.stock_quantity == 0
    assert saved.is_active is True
    assert Decimal(saved.price) == Decimal("39.90")
    assert Decimal(saved.cost_price) == Decimal("12.35")
    assert await count(sessionmaker, InventoryMovement) == 0


async def test_create_with_only_required_fields(client, admin):
    body = await create(client, admin, "Cera", "0")
    assert body["sku"] is None
    assert body["description"] is None
    assert body["cost_price"] is None
    assert body["image_url"] is None
    assert Decimal(body["price"]) == Decimal("0.00")


@pytest.mark.parametrize("deactivated", [False, True])
async def test_duplicate_name_or_sku_gets_400(client, admin, sessionmaker, deactivated):
    first = await create(client, admin, "Cera", sku="CER-1")
    if deactivated:
        await deactivate(client, admin, first["id"])

    same_name = await client.post(URL, json={"name": "Cera", "price": 5}, headers=auth(admin))
    assert same_name.status_code == 400
    assert same_name.json()["detail"] == "Já existe um produto com o nome 'Cera'."

    same_sku = await client.post(URL, json={"name": "Outra", "price": 5, "sku": "CER-1"}, headers=auth(admin))
    assert same_sku.status_code == 400
    assert same_sku.json()["detail"] == "Já existe um produto com o SKU 'CER-1'."
    assert await count(sessionmaker, Product) == 1


@pytest.mark.parametrize(
    "body",
    [
        {"name": "Cera", "price": -1},
        {"name": "Cera", "price": 5, "cost_price": -0.01},
        {"name": "x" * 151, "price": 5},
        {"name": "Cera", "price": 5, "sku": "S" * 51},
        {"price": 5},
        {"name": "Cera"},
        {"name": "Cera", "price": "caro"},
    ],
)
async def test_invalid_create_gets_422(client, admin, sessionmaker, body):
    response = await client.post(URL, json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, Product) == 0


async def test_limits_are_accepted(client, admin):
    body = await create(client, admin, "x" * 150, sku="S" * 50)
    assert len(body["name"]) == 150
    assert len(body["sku"]) == 50


# ── alteração ───────────────────────────────────────────


async def test_update_changes_only_sent_fields_and_never_the_stock(client, admin, sessionmaker):
    product = await stocked(client, admin, "Cera", 4, price="20.00", sku="CER-1", cost_price="5.00")
    response = await client.put(
        f"{URL}/{product['id']}", json={"price": "22.50", "stock_quantity": 99}, headers=auth(admin)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(body["price"]) == Decimal("22.50")
    assert body["name"] == "Cera"
    assert body["sku"] == "CER-1"
    assert Decimal(body["cost_price"]) == Decimal("5.00")
    assert body["stock_quantity"] == 4

    saved = await product_in_db(sessionmaker, product["id"])
    assert saved.stock_quantity == 4
    assert Decimal(saved.price) == Decimal("22.50")


async def test_update_every_editable_field(client, admin):
    product = await create(client, admin, "Cera")
    changes = {
        "name": "Cera Forte", "description": "Nova", "sku": "CF-2", "price": "30", "cost_price": "9",
        "image_url": "https://exemplo.com/c.png",
    }
    body = (await client.put(f"{URL}/{product['id']}", json=changes, headers=auth(admin))).json()
    assert (body["name"], body["description"], body["sku"], body["image_url"]) == (
        "Cera Forte", "Nova", "CF-2", "https://exemplo.com/c.png",
    )
    assert (Decimal(body["price"]), Decimal(body["cost_price"])) == (Decimal("30.00"), Decimal("9.00"))


async def test_update_to_another_products_name_or_sku_gets_400(client, admin, sessionmaker):
    await create(client, admin, "Cera", sku="CER-1")
    other = await create(client, admin, "Balm", sku="BAL-1")

    by_name = await client.put(f"{URL}/{other['id']}", json={"name": "Cera"}, headers=auth(admin))
    assert by_name.status_code == 400
    assert by_name.json()["detail"] == "Já existe um produto com o nome 'Cera'."

    by_sku = await client.put(f"{URL}/{other['id']}", json={"sku": "CER-1"}, headers=auth(admin))
    assert by_sku.status_code == 400
    assert by_sku.json()["detail"] == "Já existe um produto com o SKU 'CER-1'."

    saved = await product_in_db(sessionmaker, other["id"])
    assert (saved.name, saved.sku) == ("Balm", "BAL-1")


async def test_update_keeping_own_name_and_sku_is_accepted(client, admin):
    product = await create(client, admin, "Cera", sku="CER-1")
    response = await client.put(
        f"{URL}/{product['id']}", json={"name": "Cera", "sku": "CER-1", "price": 7}, headers=auth(admin)
    )
    assert response.status_code == 200, response.text
    assert Decimal(response.json()["price"]) == Decimal("7.00")


async def test_update_unknown_product_gets_404(client, admin):
    response = await client.put(f"{URL}/{uuid.uuid4()}", json={"price": 5}, headers=auth(admin))
    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


@pytest.mark.parametrize(
    "body", [{"price": -1}, {"cost_price": -1}, {"name": "x" * 151}, {"sku": "S" * 51}, {"price": "caro"}]
)
async def test_invalid_update_gets_422(client, admin, sessionmaker, body):
    product = await create(client, admin, "Cera", price="20.00")
    response = await client.put(f"{URL}/{product['id']}", json=body, headers=auth(admin))
    assert response.status_code == 422
    saved = await product_in_db(sessionmaker, product["id"])
    assert (saved.name, Decimal(saved.price), saved.sku, saved.cost_price) == ("Cera", Decimal("20.00"), None, None)


# ── desativação ─────────────────────────────────────────


async def test_deactivate_hides_from_showcase_but_keeps_the_product(client, admin, sessionmaker):
    product = await stocked(client, admin, "Cera", 3, price="15.00")
    response = await deactivate(client, admin, product["id"])
    assert response.status_code == 204
    assert response.content == b""

    assert await names(client, show_out_of_stock="true") == []
    assert (await client.get(f"{URL}/{product['id']}")).status_code == 404
    admin_list = (await client.get(f"{URL}/admin/all", headers=auth(admin))).json()
    assert [(p["name"], p["is_active"], p["stock_quantity"]) for p in admin_list] == [("Cera", False, 3)]

    saved = await product_in_db(sessionmaker, product["id"])
    assert saved.is_active is False
    assert Decimal(saved.price) == Decimal("15.00")


async def test_deactivate_twice_is_accepted(client, admin):
    product = await create(client, admin, "Cera")
    assert (await deactivate(client, admin, product["id"])).status_code == 204
    assert (await deactivate(client, admin, product["id"])).status_code == 204


async def test_deactivate_unknown_gets_404(client, admin):
    response = await deactivate(client, admin, uuid.uuid4())
    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


# ── movimentação de estoque ─────────────────────────────


async def test_restock_adds_and_records_the_movement(client, admin, sessionmaker):
    product = await create(client, admin, "Cera")
    response = await move(client, admin, product["id"], 12, "restock", "Compra do fornecedor")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == product["id"]
    assert body["stock_quantity"] == 12
    assert "cost_price" in body

    [movement] = await movements_in_db(sessionmaker)
    assert str(movement.product_id) == product["id"]
    assert movement.user_id == admin.id
    assert movement.quantity == 12
    assert movement.movement_type == MovementType.RESTOCK
    assert movement.notes == "Compra do fornecedor"
    assert (await product_in_db(sessionmaker, product["id"])).stock_quantity == 12


@pytest.mark.parametrize("kind", ["loss", "sale", "adjustment"])
async def test_negative_movement_subtracts(client, admin, sessionmaker, kind):
    product = await stocked(client, admin, "Cera", 10)
    response = await move(client, admin, product["id"], -3, kind)
    assert response.status_code == 200, response.text
    assert response.json()["stock_quantity"] == 7
    assert (await product_in_db(sessionmaker, product["id"])).stock_quantity == 7
    movements = await movements_in_db(sessionmaker)
    assert sorted((m.quantity, m.movement_type.value) for m in movements) == sorted([(10, "restock"), (-3, kind)])


async def test_movements_accumulate(client, admin):
    product = await create(client, admin, "Cera")
    for quantity, kind in [(5, "restock"), (-2, "sale"), (4, "restock"), (-1, "loss")]:
        response = await move(client, admin, product["id"], quantity, kind)
        assert response.status_code == 200
    assert response.json()["stock_quantity"] == 6


async def test_emptying_the_stock_exactly_is_accepted(client, admin):
    product = await stocked(client, admin, "Cera", 3)
    response = await move(client, admin, product["id"], -3, "loss")
    assert response.status_code == 200
    assert response.json()["stock_quantity"] == 0
    assert await names(client) == []


async def test_negative_stock_is_refused_and_nothing_changes(client, admin, sessionmaker):
    product = await stocked(client, admin, "Cera", 2)
    response = await move(client, admin, product["id"], -3, "loss")
    assert response.status_code == 400
    assert response.json()["detail"] == "Estoque insuficiente. Tentativa de remover 3, mas só existem 2 unidades."
    assert (await product_in_db(sessionmaker, product["id"])).stock_quantity == 2
    assert len(await movements_in_db(sessionmaker)) == 1


async def test_movement_on_unknown_product_gets_400(client, admin, sessionmaker):
    response = await move(client, admin, uuid.uuid4(), 5)
    assert response.status_code == 400
    assert response.json()["detail"] == NOT_FOUND
    assert await count(sessionmaker, InventoryMovement) == 0


@pytest.mark.parametrize("body", [{"quantity": 5, "movement_type": "doacao"}, {"movement_type": "restock"},
                                  {"quantity": 5}, {"quantity": "cinco", "movement_type": "restock"}])
async def test_invalid_movement_gets_422(client, admin, sessionmaker, body):
    product = await create(client, admin, "Cera")
    response = await client.post(f"{URL}/{product['id']}/inventory", json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, InventoryMovement) == 0


# ── histórico ───────────────────────────────────────────


async def test_history_lists_only_this_products_movements_newest_first(client, admin):
    product = await create(client, admin, "Cera")
    other = await create(client, admin, "Balm")
    await move(client, admin, product["id"], 5, "restock", "primeira")
    await move(client, admin, other["id"], 9, "restock", "do outro")
    await move(client, admin, product["id"], -2, "loss", "segunda")

    response = await client.get(f"{URL}/{product['id']}/inventory", headers=auth(admin))
    assert response.status_code == 200
    body = response.json()
    assert [(m["quantity"], m["movement_type"], m["notes"]) for m in body] == [
        (-2, "loss", "segunda"),
        (5, "restock", "primeira"),
    ]
    assert all(m["product_id"] == product["id"] and m["user_id"] == str(admin.id) for m in body)
    assert all(m["id"] and m["created_at"] for m in body)


async def test_history_of_product_without_movements_is_empty(client, admin):
    product = await create(client, admin, "Cera")
    response = await client.get(f"{URL}/{product['id']}/inventory", headers=auth(admin))
    assert response.status_code == 200
    assert response.json() == []


async def test_history_of_unknown_product_gets_404(client, admin):
    response = await client.get(f"{URL}/{uuid.uuid4()}/inventory", headers=auth(admin))
    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


# ── permissões ──────────────────────────────────────────


@pytest.mark.parametrize("role", [None, UserRole.CLIENT, UserRole.BARBER])
async def test_admin_routes_are_forbidden_to_others(client, admin, sessionmaker, role):
    product = await stocked(client, admin, "Cera", 2, price="10.00")
    pid = product["id"]
    headers = auth(await add_user(sessionmaker, "outro@teste.com", role)) if role else {}
    requests = [
        ("get", f"{URL}/admin/all", None),
        ("post", URL, {"name": "Nova", "price": 1}),
        ("put", f"{URL}/{pid}", {"price": 99}),
        ("delete", f"{URL}/{pid}", None),
        ("post", f"{URL}/{pid}/inventory", {"quantity": -2, "movement_type": "loss"}),
        ("get", f"{URL}/{pid}/inventory", None),
    ]
    for method, url, body in requests:
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        response = await getattr(client, method)(url, **kwargs)
        assert response.status_code == 403, (method, url, response.text)

    saved = await product_in_db(sessionmaker, pid)
    assert (saved.is_active, saved.stock_quantity, Decimal(saved.price)) == (True, 2, Decimal("10.00"))
    assert await count(sessionmaker, Product) == 1
    assert await count(sessionmaker, InventoryMovement) == 1


async def test_showcase_and_details_are_public(client, admin):
    product = await stocked(client, admin, "Cera", 1)
    assert (await client.get(URL)).status_code == 200
    assert (await client.get(f"{URL}/{product['id']}")).status_code == 200
