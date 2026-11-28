"""
Plano do Trim Club com cortes ou barbas ilimitados: null = ilimitado (#16).

Spec: SPEC/2026-11-25-alembic-migracoes.md
"""

import pytest
import pytest_asyncio

from src.backend.modules.auth.models import UserRole
from tests.agenda_fixtures import needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/subscriptions/plans"


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


async def create(client, admin, **body):
    response = await client.post(URL, json={"name": "Executivo", "monthly_price": "150.00", **body}, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


async def test_null_means_unlimited(client, admin):
    plan = await create(client, admin, included_cuts=None, included_shaves=2)
    assert (plan["included_cuts"], plan["included_shaves"]) == (None, 2)
    public = (await client.get(URL)).json()
    assert public[0]["included_cuts"] is None


async def test_omitted_means_not_included(client, admin):
    plan = await create(client, admin)
    assert (plan["included_cuts"], plan["included_shaves"]) == (0, 0)


async def test_put_can_switch_between_limited_and_unlimited(client, admin):
    plan = await create(client, admin, included_cuts=4)
    url = f"{URL}/{plan['id']}"
    assert (await client.put(url, json={"included_cuts": None}, headers=auth(admin))).json()["included_cuts"] is None
    assert (await client.put(url, json={"included_cuts": 8}, headers=auth(admin))).json()["included_cuts"] == 8
    # Um PUT sem o campo não mexe nele.
    assert (await client.put(url, json={"monthly_price": "160"}, headers=auth(admin))).json()["included_cuts"] == 8


@pytest.mark.parametrize("field", ["included_cuts", "included_shaves"])
async def test_negative_is_still_refused(client, sessionmaker, admin, field):
    response = await client.post(URL, json={"name": "P", "monthly_price": 10, field: -1}, headers=auth(admin))
    assert response.status_code == 422
