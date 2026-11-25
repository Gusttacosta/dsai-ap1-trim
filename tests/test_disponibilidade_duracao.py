"""
Disponibilidade só aceita duração entre 1 minuto e 24 horas (#57).

Spec: SPEC/2026-11-25-disponibilidade-duracao.md
"""

from datetime import date

import pytest
import pytest_asyncio

from tests.agenda_fixtures import brt, create_shop, needs_db

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/appointments/availability"
DAY = date(2026, 12, 2)  # quarta-feira; o expediente de create_shop é 09:00 às 18:00


@pytest_asyncio.fixture
async def shop(sessionmaker, set_now):
    set_now(brt(2026, 12, 1, 8, 0))
    return await create_shop(sessionmaker)


async def ask(client, shop, duration):
    params = {"barber_id": str(shop["barber_id"]), "target_date": DAY.isoformat(), "duration_minutes": duration}
    return await client.get(URL, params=params)


@pytest.mark.parametrize("duration", [0, -30, -1, 1441, 100000])
async def test_duration_out_of_range_gets_422(client, shop, duration):
    response = await ask(client, shop, duration)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "duration_minutes"]


@pytest.mark.parametrize("duration", [1, 1440])
async def test_edges_are_accepted(client, shop, duration):
    assert (await ask(client, shop, duration)).status_code == 200


@pytest.mark.parametrize(
    "duration, expected",
    [
        (30, [f"{h:02d}:{m:02d}" for h in range(9, 18) for m in (0, 30)]),
        (540, ["09:00"]),
        (541, []),
    ],
)
async def test_valid_durations_keep_working(client, shop, duration, expected):
    response = await ask(client, shop, duration)
    assert response.status_code == 200, response.text
    assert response.json()["available_slots"] == expected
