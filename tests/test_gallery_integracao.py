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


# ── galeria pública ─────────────────────────────────────


@pytest_asyncio.fixture
async def portfolio(client, admin, ana, bruno):
    """Três fotos aprovadas (Ana com Degradê, Ana sem tag, Bruno com Degradê) e uma pendente."""
    fade = await add_tag(client, admin, "Degradê")
    ana_fade = await upload(client, ana[1], "https://x.com/ana-1.jpg", tag_ids=[fade["id"]])
    ana_plain = await upload(client, ana[1], "https://x.com/ana-2.jpg")
    bruno_fade = await upload(client, bruno[1], "https://x.com/bruno-1.jpg", tag_ids=[fade["id"]])
    pending = await upload(client, ana[1], "https://x.com/ana-3.jpg", tag_ids=[fade["id"]])
    for image in (ana_fade, ana_plain, bruno_fade):
        assert (await approve(client, admin, image["id"])).status_code == 200
    return {"fade": fade, "ana_fade": ana_fade["id"], "ana_plain": ana_plain["id"],
            "bruno_fade": bruno_fade["id"], "pending": pending["id"]}


async def test_public_gallery_shows_approved_newest_first(client, portfolio):
    assert await public(client) == [portfolio["bruno_fade"], portfolio["ana_plain"], portfolio["ana_fade"]]
    body = (await client.get(URL)).json()
    assert [t["name"] for t in body[0]["tags"]] == ["Degradê"]
    assert all(i["is_approved"] for i in body)


async def test_public_gallery_filters(client, portfolio, ana, bruno):
    p = portfolio
    assert await public(client, barber_id=str(ana[0].id)) == [p["ana_plain"], p["ana_fade"]]
    assert await public(client, barber_id=str(bruno[0].id)) == [p["bruno_fade"]]
    assert await public(client, tag_id=p["fade"]["id"]) == [p["bruno_fade"], p["ana_fade"]]
    assert await public(client, barber_id=str(ana[0].id), tag_id=p["fade"]["id"]) == [p["ana_fade"]]
    assert await public(client, barber_id=str(uuid.uuid4())) == []


async def test_empty_public_gallery(client, sessionmaker):
    assert await public(client) == []


# ── pendentes e aprovação ───────────────────────────────


async def test_pending_lists_only_unapproved_newest_first(client, admin, ana, bruno):
    first = await upload(client, ana[1], "https://x.com/1.jpg")
    approved = await upload(client, ana[1], "https://x.com/2.jpg")
    last = await upload(client, bruno[1], "https://x.com/3.jpg")
    await approve(client, admin, approved["id"])

    response = await client.get(f"{URL}/pending", headers=auth(admin))
    assert response.status_code == 200
    assert [i["id"] for i in response.json()] == [last["id"], first["id"]]
    assert not any(i["is_approved"] for i in response.json())


async def test_approve_moves_the_photo_to_the_public_gallery(client, admin, ana, sessionmaker):
    image = await upload(client, ana[1])
    response = await approve(client, admin, image["id"])
    assert response.status_code == 200, response.text
    assert response.json()["is_approved"] is True
    assert response.json()["id"] == image["id"]
    assert (await image_in_db(sessionmaker, image["id"])).is_approved is True
    assert await public(client) == [image["id"]]
    assert (await client.get(f"{URL}/pending", headers=auth(admin))).json() == []

    again = await approve(client, admin, image["id"])
    assert again.status_code == 200
    assert again.json()["is_approved"] is True


async def test_approve_unknown_photo_gets_404(client, admin):
    response = await approve(client, admin, uuid.uuid4())
    assert response.status_code == 404
    assert response.json()["detail"] == NOT_FOUND


# ── exclusão ────────────────────────────────────────────


async def test_barber_deletes_own_photo_and_its_tag_links(client, admin, ana, sessionmaker):
    fade = await add_tag(client, admin, "Degradê")
    image = await upload(client, ana[1], tag_ids=[fade["id"]])
    await approve(client, admin, image["id"])

    response = await client.delete(f"{URL}/{image['id']}", headers=auth(ana[1]))
    assert response.status_code == 204
    assert await image_in_db(sessionmaker, image["id"]) is None
    assert await public(client) == []
    assert await tag_links(sessionmaker) == 0
    assert await count(sessionmaker, GalleryTag) == 1


async def test_barber_cannot_delete_another_barbers_photo(client, ana, bruno, sessionmaker):
    image = await upload(client, ana[1])
    response = await client.delete(f"{URL}/{image['id']}", headers=auth(bruno[1]))
    assert response.status_code == 403
    assert response.json()["detail"] == NOT_YOURS
    assert await image_in_db(sessionmaker, image["id"]) is not None


async def test_admin_deletes_any_photo(client, admin, ana, sessionmaker):
    image = await upload(client, ana[1])
    assert (await client.delete(f"{URL}/{image['id']}", headers=auth(admin))).status_code == 204
    assert await count(sessionmaker, PortfolioImage) == 0


async def test_delete_unknown_photo_gets_404(client, admin, ana):
    for user in (admin, ana[1]):
        response = await client.delete(f"{URL}/{uuid.uuid4()}", headers=auth(user))
        assert response.status_code == 404
        assert response.json()["detail"] == NOT_FOUND


# ── permissões ──────────────────────────────────────────


@pytest.mark.parametrize("role", [None, UserRole.CLIENT])
async def test_moderation_is_forbidden_to_visitors_and_clients(client, admin, ana, sessionmaker, role):
    image = await upload(client, ana[1])
    headers = auth(await add_user(sessionmaker, "outro@teste.com", role)) if role else {}
    responses = [
        await client.post(f"{URL}/tags", json={"name": "Nova"}, headers=headers),
        await client.post(URL, json={"image_url": "https://x.com/b.jpg"}, headers=headers),
        await client.get(f"{URL}/pending", headers=headers),
        await client.put(f"{URL}/{image['id']}/approve", headers=headers),
        await client.delete(f"{URL}/{image['id']}", headers=headers),
    ]
    assert [r.status_code for r in responses] == [403] * 5
    saved = await image_in_db(sessionmaker, image["id"])
    assert saved is not None and saved.is_approved is False
    assert (await count(sessionmaker, PortfolioImage), await count(sessionmaker, GalleryTag)) == (1, 0)


async def test_admin_only_routes_are_forbidden_to_barbers(client, ana, sessionmaker):
    image = await upload(client, ana[1])
    responses = [
        await client.post(f"{URL}/tags", json={"name": "Nova"}, headers=auth(ana[1])),
        await client.get(f"{URL}/pending", headers=auth(ana[1])),
        await client.put(f"{URL}/{image['id']}/approve", headers=auth(ana[1])),
    ]
    assert [r.status_code for r in responses] == [403] * 3
    assert (await image_in_db(sessionmaker, image["id"])).is_approved is False
    assert await count(sessionmaker, GalleryTag) == 0


async def test_gallery_and_tags_are_public(client, admin, ana):
    await add_tag(client, admin, "Barba")
    image = await upload(client, ana[1])
    await approve(client, admin, image["id"])
    assert (await client.get(f"{URL}/tags")).status_code == 200
    assert await public(client) == [image["id"]]
