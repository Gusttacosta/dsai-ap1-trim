"""
Galeria: envio pelo admin, tags (desconhecidas, vazias, renomear e apagar) e moderação (recusar
com motivo, tirar a aprovação e esconder barbeiro desativado) (#71).

Spec: SPEC/2026-11-25-galeria-permissoes.md
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber
from src.backend.modules.gallery.models import GalleryTag, PortfolioImage
from src.backend.modules.notifications.models import Notification
from tests.agenda_fixtures import count, needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/gallery"
PHOTO = "https://fotos.exemplo.com/corte.jpg"


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


async def upload(client, user, **extra):
    return await client.post(URL, json={"image_url": PHOTO, **extra}, headers=auth(user))


async def uploaded(client, user, **extra):
    response = await upload(client, user, **extra)
    assert response.status_code == 201, response.text
    return response.json()


async def new_tag(client, admin, name="Degradê"):
    response = await client.post(f"{URL}/tags", json={"name": name}, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


async def public_ids(client):
    return [i["id"] for i in (await client.get(URL)).json()]


# ── item 2: admin envia em nome de um barbeiro ──────────


async def test_admin_without_profile_uploads_for_a_barber_already_approved(client, sessionmaker, admin, ana):
    body = await uploaded(client, admin, barber_id=str(ana[0].id))
    assert body["barber_id"] == str(ana[0].id)
    assert body["is_approved"] is True
    assert await public_ids(client) == [body["id"]]


async def test_admin_without_profile_must_name_the_barber(client, sessionmaker, admin):
    response = await upload(client, admin)
    assert response.status_code == 400
    assert response.json()["detail"] == "Informe o barbeiro da foto (barber_id)."
    assert await count(sessionmaker, PortfolioImage) == 0


@pytest.mark.parametrize("barber", ["desconhecido", "desativado"])
async def test_admin_upload_for_unknown_or_inactive_barber_gets_404(client, sessionmaker, admin, ana, barber):
    if barber == "desativado":
        async with sessionmaker() as db:
            await db.execute(update(Barber).values(is_active=False))
            await db.commit()
        barber_id = ana[0].id
    else:
        barber_id = uuid.uuid4()
    response = await upload(client, admin, barber_id=str(barber_id))
    assert response.status_code == 404
    assert await count(sessionmaker, PortfolioImage) == 0


async def test_barber_cannot_upload_to_another_portfolio(client, sessionmaker, ana):
    other, _ = await barber_user(sessionmaker, "bruno@teste.com")
    response = await upload(client, ana[1], barber_id=str(other.id))
    assert response.status_code == 403
    assert await count(sessionmaker, PortfolioImage) == 0


async def test_barber_naming_own_portfolio_is_fine(client, ana):
    assert (await uploaded(client, ana[1], barber_id=str(ana[0].id)))["barber_id"] == str(ana[0].id)


# ── item 3: tags ────────────────────────────────────────


async def test_unknown_tag_on_upload_gets_404(client, sessionmaker, admin, ana):
    tag = await new_tag(client, admin)
    response = await upload(client, ana[1], tag_ids=[tag["id"], str(uuid.uuid4())])
    assert response.status_code == 404
    assert response.json()["detail"] == "Uma ou mais tags não existem."
    assert await count(sessionmaker, PortfolioImage) == 0


async def test_repeated_tag_id_is_accepted_once(client, admin, ana):
    tag = await new_tag(client, admin)
    body = await uploaded(client, ana[1], tag_ids=[tag["id"], tag["id"]])
    assert [t["name"] for t in body["tags"]] == ["Degradê"]


@pytest.mark.parametrize("name", ["", "   "])
async def test_blank_tag_name_gets_422(client, sessionmaker, admin, name):
    assert (await client.post(f"{URL}/tags", json={"name": name}, headers=auth(admin))).status_code == 422
    tag = await new_tag(client, admin)
    assert (await client.put(f"{URL}/tags/{tag['id']}", json={"name": name}, headers=auth(admin))).status_code == 422
    assert await count(sessionmaker, GalleryTag) == 1


async def test_admin_renames_tag(client, admin, ana):
    tag = await new_tag(client, admin, "Degrade")
    image = await uploaded(client, ana[1], tag_ids=[tag["id"]])

    response = await client.put(f"{URL}/tags/{tag['id']}", json={"name": "Degradê"}, headers=auth(admin))

    assert response.status_code == 200
    assert response.json()["name"] == "Degradê"
    await client.put(f"{URL}/{image['id']}/approve", headers=auth(admin))
    assert (await client.get(URL)).json()[0]["tags"][0]["name"] == "Degradê"


async def test_rename_to_existing_tag_gets_400(client, admin):
    await new_tag(client, admin, "Barba")
    tag = await new_tag(client, admin, "Degradê")
    response = await client.put(f"{URL}/tags/{tag['id']}", json={"name": "Barba"}, headers=auth(admin))
    assert response.status_code == 400
    assert response.json()["detail"] == "A tag 'Barba' já existe."


async def test_delete_tag_keeps_the_photos(client, sessionmaker, admin, ana):
    tag = await new_tag(client, admin)
    image = await uploaded(client, ana[1], tag_ids=[tag["id"]])

    assert (await client.delete(f"{URL}/tags/{tag['id']}", headers=auth(admin))).status_code == 204

    assert await count(sessionmaker, GalleryTag) == 0
    pending = (await client.get(f"{URL}/pending", headers=auth(admin))).json()
    assert [(p["id"], p["tags"]) for p in pending] == [(image["id"], [])]


@pytest.mark.parametrize("method", ["put", "delete"])
async def test_unknown_tag_gets_404(client, admin, method):
    url = f"{URL}/tags/{uuid.uuid4()}"
    response = await (client.put(url, json={"name": "X"}, headers=auth(admin)) if method == "put"
                      else client.delete(url, headers=auth(admin)))
    assert response.status_code == 404
    assert response.json()["detail"] == "Tag não encontrada."


# ── item 4: moderação ───────────────────────────────────


async def test_reject_deletes_the_photo_and_tells_the_barber_why(client, sessionmaker, admin, ana):
    image = await uploaded(client, ana[1])

    response = await client.put(f"{URL}/{image['id']}/reject", json={"reason": "Foto desfocada"}, headers=auth(admin))

    assert response.status_code == 204
    assert await count(sessionmaker, PortfolioImage) == 0
    async with sessionmaker() as db:
        [notice] = (await db.execute(select(Notification))).scalars().all()
    assert notice.user_id == ana[1].id
    assert notice.title == "Foto recusada na galeria"
    assert "Motivo: Foto desfocada" in notice.message
    mine = (await client.get("/api/notifications", headers=auth(ana[1]))).json()
    assert [n["title"] for n in mine] == ["Foto recusada na galeria"]


@pytest.mark.parametrize("body", [{}, {"reason": ""}, {"reason": "   "}, {"reason": "x" * 501}])
async def test_reject_needs_a_reason(client, sessionmaker, admin, ana, body):
    image = await uploaded(client, ana[1])
    response = await client.put(f"{URL}/{image['id']}/reject", json=body, headers=auth(admin))
    assert response.status_code == 422
    assert await count(sessionmaker, PortfolioImage) == 1


async def test_approved_photo_is_not_rejected(client, sessionmaker, admin, ana):
    image = await uploaded(client, ana[1])
    await client.put(f"{URL}/{image['id']}/approve", headers=auth(admin))
    response = await client.put(f"{URL}/{image['id']}/reject", json={"reason": "x"}, headers=auth(admin))
    assert response.status_code == 400
    assert await count(sessionmaker, PortfolioImage) == 1


async def test_unapprove_takes_the_photo_back_to_moderation(client, sessionmaker, admin, ana):
    image = await uploaded(client, ana[1])
    await client.put(f"{URL}/{image['id']}/approve", headers=auth(admin))
    assert await public_ids(client) == [image["id"]]

    response = await client.put(f"{URL}/{image['id']}/unapprove", headers=auth(admin))

    assert response.status_code == 200
    assert response.json()["is_approved"] is False
    assert await public_ids(client) == []
    pending = (await client.get(f"{URL}/pending", headers=auth(admin))).json()
    assert [p["id"] for p in pending] == [image["id"]]


@pytest.mark.parametrize("action", ["unapprove", "reject"])
async def test_moderating_unknown_photo_gets_404(client, admin, action):
    kwargs = {"json": {"reason": "x"}} if action == "reject" else {}
    response = await client.put(f"{URL}/{uuid.uuid4()}/{action}", headers=auth(admin), **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"] == "Imagem não encontrada."


@pytest.mark.parametrize("action", ["unapprove", "reject"])
async def test_moderation_is_admin_only(client, sessionmaker, admin, ana, action):
    image = await uploaded(client, ana[1])
    kwargs = {"json": {"reason": "x"}} if action == "reject" else {}
    response = await client.put(f"{URL}/{image['id']}/{action}", headers=auth(ana[1]), **kwargs)
    assert response.status_code == 403
    assert await count(sessionmaker, PortfolioImage) == 1


@pytest.mark.parametrize("what", ["perfil", "conta"])
async def test_deactivated_barbers_photos_leave_the_public_gallery(client, sessionmaker, admin, ana, what):
    other, bruno = await barber_user(sessionmaker, "bruno@teste.com")
    ana_photo = await uploaded(client, admin, barber_id=str(ana[0].id))
    bruno_photo = await uploaded(client, admin, barber_id=str(other.id))
    assert sorted(await public_ids(client)) == sorted([ana_photo["id"], bruno_photo["id"]])

    async with sessionmaker() as db:
        if what == "perfil":
            await db.execute(update(Barber).where(Barber.id == ana[0].id).values(is_active=False))
        else:
            await db.execute(update(User).where(User.id == ana[1].id).values(is_active=False))
        await db.commit()

    assert await public_ids(client) == [bruno_photo["id"]]
    filtered = (await client.get(URL, params={"barber_id": str(ana[0].id)})).json()
    assert filtered == []
