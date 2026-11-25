"""
Galeria: barbeiro sem perfil não apaga foto alheia, e envios inválidos param de dar 500 (#71).

Spec: SPEC/2026-11-25-galeria-permissoes.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`, que também
faz o override do `get_db`), com um schema novo a cada teste.
"""

import uuid

import pytest
import pytest_asyncio

from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.gallery.models import PortfolioImage
from src.backend.modules.gallery.service import GalleryService
from src.backend.modules.services.models import Service
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/gallery"
NO_PROFILE = "Perfil de barbeiro não encontrado."
NOT_YOURS = "Você não tem permissão para deletar a foto de outro barbeiro."
PHOTO = "https://fotos.exemplo.com/corte.jpg"


# ── apoio ───────────────────────────────────────────────


async def barber_user(maker, email):
    barber = await add_barber(maker, email)
    async with maker() as db:
        return barber, await db.get(User, barber.user_id)


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


@pytest_asyncio.fixture
async def ana(sessionmaker):
    return await barber_user(sessionmaker, "ana@teste.com")


@pytest_asyncio.fixture
async def bruno(sessionmaker):
    return await barber_user(sessionmaker, "bruno@teste.com")


@pytest_asyncio.fixture
async def no_profile(sessionmaker):
    """Conta promovida a barbeiro que ainda não tem linha em `barbers`."""
    return await add_user(sessionmaker, "sem.perfil@teste.com", UserRole.BARBER)


async def upload(client, user, **extra):
    body = {"image_url": PHOTO, **extra}
    return await client.post(URL, json=body, headers=auth(user))


async def photo_of(client, user):
    response = await upload(client, user)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def exists(maker, image_id):
    async with maker() as db:
        return await db.get(PortfolioImage, uuid.UUID(str(image_id))) is not None


async def delete(client, user, image_id):
    return await client.delete(f"{URL}/{image_id}", headers=auth(user))


# ── item 1: exclusão ────────────────────────────────────


async def test_barber_without_profile_cannot_delete_someone_elses_photo(
    client, sessionmaker, ana, no_profile
):
    image_id = await photo_of(client, ana[1])

    response = await delete(client, no_profile, image_id)

    assert response.status_code == 403
    assert response.json()["detail"] == NO_PROFILE
    assert await exists(sessionmaker, image_id)


async def test_barber_without_profile_gets_403_even_for_unknown_photo(client, sessionmaker, no_profile):
    response = await delete(client, no_profile, uuid.uuid4())
    assert response.status_code == 403
    assert response.json()["detail"] == NO_PROFILE


async def test_barber_deletes_own_photo(client, sessionmaker, ana):
    image_id = await photo_of(client, ana[1])

    response = await delete(client, ana[1], image_id)

    assert response.status_code == 204
    assert not await exists(sessionmaker, image_id)


async def test_barber_cannot_delete_another_barbers_photo(client, sessionmaker, ana, bruno):
    image_id = await photo_of(client, ana[1])

    response = await delete(client, bruno[1], image_id)

    assert response.status_code == 403
    assert response.json()["detail"] == NOT_YOURS
    assert await exists(sessionmaker, image_id)


async def test_admin_without_profile_deletes_any_photo(client, sessionmaker, admin, ana):
    image_id = await photo_of(client, ana[1])

    response = await delete(client, admin, image_id)

    assert response.status_code == 204
    assert not await exists(sessionmaker, image_id)


async def test_unknown_photo_is_404_for_barber_and_admin(client, sessionmaker, admin, ana):
    for user in (ana[1], admin):
        response = await delete(client, user, uuid.uuid4())
        assert response.status_code == 404
        assert response.json()["detail"] == "Imagem não encontrada."


async def test_service_checks_ownership_when_not_admin_even_without_barber(sessionmaker, ana):
    """Defesa no serviço: sem `is_admin`, um id de barbeiro ausente não vale como permissão."""
    async with sessionmaker() as db:
        image = PortfolioImage(image_url=PHOTO, barber_id=ana[0].id, is_approved=True)
        db.add(image)
        await db.commit()
        image_id = image.id

    async with sessionmaker() as db:
        with pytest.raises(ValueError, match="outro barbeiro"):
            await GalleryService(db).delete_image(image_id, None)
    assert await exists(sessionmaker, image_id)

    async with sessionmaker() as db:
        assert await GalleryService(db).delete_image(image_id, None, is_admin=True) is True
    assert not await exists(sessionmaker, image_id)


# ── item 3: envios que davam 500 ────────────────────────


async def test_unknown_service_gets_404_and_saves_nothing(client, sessionmaker, ana):
    response = await upload(client, ana[1], service_id=str(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["detail"] == "Serviço não encontrado."
    assert await count(sessionmaker, PortfolioImage) == 0


async def test_known_service_is_still_accepted(client, sessionmaker, ana):
    async with sessionmaker() as db:
        service = Service(name="Corte", price=40, duration_minutes=30)
        db.add(service)
        await db.commit()

    response = await upload(client, ana[1], service_id=str(service.id))

    assert response.status_code == 201, response.text
    assert response.json()["service_id"] == str(service.id)


def url_of(length):
    base = "https://fotos.exemplo.com/"
    return base + "a" * (length - len(base))


async def test_image_url_over_1000_chars_gets_422(client, sessionmaker, ana):
    response = await client.post(URL, json={"image_url": url_of(1001)}, headers=auth(ana[1]))

    assert response.status_code == 422
    assert "1000" in response.text
    assert await count(sessionmaker, PortfolioImage) == 0


async def test_image_url_with_exactly_1000_chars_is_accepted(client, sessionmaker, ana):
    response = await client.post(URL, json={"image_url": url_of(1000)}, headers=auth(ana[1]))

    assert response.status_code == 201, response.text
    assert len(response.json()["image_url"]) == 1000
