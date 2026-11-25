"""
Testes de integração da galeria de fotos (#3).

Spec: SPEC/2026-11-24-testes-integracao-gallery.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Substituem o tests/test_gallery.py gerado, que não importava a aplicação.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber
from src.backend.modules.gallery.models import GalleryTag, PortfolioImage, portfolio_image_tags
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/gallery"
NOT_FOUND = "Imagem não encontrada."
NOT_YOURS = "Você não tem permissão para deletar a foto de outro barbeiro."


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


async def barber_with_user(maker, email):
    barber = await add_barber(maker, email)
    async with maker() as db:
        return barber, await db.get(User, barber.user_id)


@pytest_asyncio.fixture
async def ana(sessionmaker):
    return await barber_with_user(sessionmaker, "ana@teste.com")


@pytest_asyncio.fixture
async def bruno(sessionmaker):
    return await barber_with_user(sessionmaker, "bruno@teste.com")


async def add_tag(client, admin, name):
    response = await client.post(f"{URL}/tags", json={"name": name}, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


async def upload(client, user, url="https://fotos.exemplo.com/corte.jpg", **extra):
    response = await client.post(URL, json={"image_url": url, **extra}, headers=auth(user))
    assert response.status_code == 201, response.text
    return response.json()


async def approve(client, admin, image_id):
    return await client.put(f"{URL}/{image_id}/approve", headers=auth(admin))


async def public(client, **params):
    response = await client.get(URL, params=params)
    assert response.status_code == 200, response.text
    return [i["id"] for i in response.json()]


async def image_in_db(maker, image_id):
    async with maker() as db:
        return await db.get(PortfolioImage, uuid.UUID(str(image_id)))


async def tag_links(maker):
    async with maker() as db:
        return (await db.execute(select(func.count()).select_from(portfolio_image_tags))).scalar_one()


# ── tags ────────────────────────────────────────────────


async def test_tags_are_created_and_listed_alphabetically(client, admin):
    fade = await add_tag(client, admin, "Degradê")
    assert fade["name"] == "Degradê" and fade["id"]
    await add_tag(client, admin, "Barba")
    await add_tag(client, admin, "Navalhado")

    response = await client.get(f"{URL}/tags")
    assert response.status_code == 200
    assert [t["name"] for t in response.json()] == ["Barba", "Degradê", "Navalhado"]


async def test_duplicate_tag_gets_400(client, admin, sessionmaker):
    await add_tag(client, admin, "Barba")
    response = await client.post(f"{URL}/tags", json={"name": "Barba"}, headers=auth(admin))
    assert response.status_code == 400
    assert response.json()["detail"] == "A tag 'Barba' já existe."
    assert await count(sessionmaker, GalleryTag) == 1


@pytest.mark.parametrize("body", [{"name": "x" * 51}, {}])
async def test_invalid_tag_gets_422(client, admin, sessionmaker, body):
    response = await client.post(f"{URL}/tags", json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, GalleryTag) == 0


async def test_no_tags(client, sessionmaker):
    assert (await client.get(f"{URL}/tags")).json() == []


# ── envio de fotos ──────────────────────────────────────


async def test_barber_upload_waits_for_approval(client, admin, ana, sessionmaker):
    barber, user = ana
    fade = await add_tag(client, admin, "Degradê")
    beard = await add_tag(client, admin, "Barba")
    body = await upload(
        client, user, "https://fotos.exemplo.com/ana-1.jpg", description="Degradê com barba",
        tag_ids=[fade["id"], beard["id"]],
    )
    assert body["is_approved"] is False
    assert body["barber_id"] == str(barber.id)
    assert body["image_url"] == "https://fotos.exemplo.com/ana-1.jpg"
    assert body["description"] == "Degradê com barba"
    assert body["service_id"] is None
    assert sorted(t["name"] for t in body["tags"]) == ["Barba", "Degradê"]
    assert body["created_at"]

    saved = await image_in_db(sessionmaker, body["id"])
    assert (saved.is_approved, saved.barber_id) == (False, barber.id)
    assert await tag_links(sessionmaker) == 2
    assert await public(client) == []


async def test_upload_can_name_the_service(client, ana, sessionmaker):
    from src.backend.modules.services.models import Service

    async with sessionmaker() as db:
        service = Service(name="Corte", price=40, duration_minutes=30)
        db.add(service)
        await db.commit()
    body = await upload(client, ana[1], service_id=str(service.id))
    assert body["service_id"] == str(service.id)
    assert body["tags"] == []


async def test_admin_with_barber_profile_uploads_already_approved(client, admin, sessionmaker):
    async with sessionmaker() as db:
        profile = Barber(user_id=admin.id)
        db.add(profile)
        await db.commit()
    body = await upload(client, admin)
    assert body["is_approved"] is True
    assert body["barber_id"] == str(profile.id)
    assert await public(client) == [body["id"]]


async def test_barber_without_profile_gets_404(client, sessionmaker):
    orphan = await add_user(sessionmaker, "orfao@teste.com", UserRole.BARBER)
    response = await client.post(URL, json={"image_url": "https://x.com/a.jpg"}, headers=auth(orphan))
    assert response.status_code == 404
    assert response.json()["detail"] == "Perfil de barbeiro não encontrado."
    assert await count(sessionmaker, PortfolioImage) == 0


@pytest.mark.parametrize(
    "body",
    [{"image_url": "ftp://x.com/a.jpg"}, {"image_url": "nao-e-url"}, {},
     {"image_url": "https://x.com/a.jpg", "description": "x" * 501},
     {"image_url": "https://x.com/a.jpg", "tag_ids": ["nao-e-uuid"]}],
)
async def test_invalid_upload_gets_422(client, ana, sessionmaker, body):
    response = await client.post(URL, json=body, headers=auth(ana[1]))
    assert response.status_code == 422
    assert await count(sessionmaker, PortfolioImage) == 0
