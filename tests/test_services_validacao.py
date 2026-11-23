"""
Validação dos campos, reativação e vínculos do catálogo de serviços (#39).

Spec: SPEC/2026-11-22-servicos-validacao-reativacao.md

Escritos antes da correção: com o código anterior, os casos de null e de valor acima da coluna
davam 500 (IntegrityError ou DataError), e os outros passavam sem erro.
"""

from decimal import Decimal

import pytest
from sqlalchemy import update

from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber
from src.backend.modules.services.models import BarberServiceAssociation, Service
from tests.agenda_fixtures import needs_db
from tests.api_helpers import add_barber, add_user, auth
from tests.test_services_integracao import URL, admin, barber_ids, count, create, link, names, service_in_db  # noqa: F401

pytestmark = [pytest.mark.asyncio, needs_db]

MAX_PRICE = "99999999.99"
REACTIVATE = "Já existe um serviço desativado com o nome 'Corte'. Reative-o em vez de criar outro."


async def update_service(client, admin, service_id, changes):
    return await client.put(f"{URL}/{service_id}", json=changes, headers=auth(admin))


async def deactivate(client, admin, service_id):
    response = await client.delete(f"{URL}/{service_id}", headers=auth(admin))
    assert response.status_code == 204


def stored_fields(service):
    return (service.name, service.price, service.duration_minutes, service.is_active)


# ── null na alteração ───────────────────────────────────


@pytest.mark.parametrize("field", ["name", "price", "duration_minutes", "is_active"])
async def test_null_em_campo_obrigatorio_responde_422(sessionmaker, client, admin, field):
    corte = await create(client, admin)

    response = await update_service(client, admin, corte["id"], {field: None})

    assert response.status_code == 422
    assert stored_fields(await service_in_db(sessionmaker, corte["id"])) == ("Corte", Decimal("40.00"), 30, True)


async def test_null_na_descricao_continua_apagando(sessionmaker, client, admin):
    corte = await create(client, admin, description="Na tesoura")

    response = await update_service(client, admin, corte["id"], {"description": None})

    assert response.status_code == 200
    assert (await service_in_db(sessionmaker, corte["id"])).description is None


# ── limites das colunas ─────────────────────────────────


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Corte", "price": "100000000.00", "duration_minutes": 30},
        {"name": "Corte", "price": 40, "duration_minutes": 721},
        {"name": "Corte", "price": 40, "duration_minutes": 2**31},
    ],
    ids=["preco-acima-da-coluna", "duracao-acima-de-12h", "duracao-acima-do-integer"],
)
async def test_criacao_acima_dos_limites_responde_422(sessionmaker, client, admin, payload):
    response = await client.post(URL, json=payload, headers=auth(admin))

    assert response.status_code == 422
    assert await count(sessionmaker, Service) == 0


@pytest.mark.parametrize(
    "changes",
    [{"price": "100000000"}, {"duration_minutes": 721}, {"duration_minutes": 2**31}],
    ids=["preco-acima-da-coluna", "duracao-acima-de-12h", "duracao-acima-do-integer"],
)
async def test_alteracao_acima_dos_limites_responde_422(sessionmaker, client, admin, changes):
    corte = await create(client, admin)

    response = await update_service(client, admin, corte["id"], changes)

    assert response.status_code == 422
    assert stored_fields(await service_in_db(sessionmaker, corte["id"])) == ("Corte", Decimal("40.00"), 30, True)


async def test_limites_maximos_sao_aceitos(sessionmaker, client, admin):
    body = await create(client, admin, price=MAX_PRICE, duration=720)

    stored = await service_in_db(sessionmaker, body["id"])
    assert (stored.price, stored.duration_minutes) == (Decimal(MAX_PRICE), 720)


# ── nome ────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["", "   ", "x", " x "])
async def test_nome_vazio_ou_curto_responde_422(sessionmaker, client, admin, name):
    response = await client.post(URL, json={"name": name, "price": 40, "duration_minutes": 30}, headers=auth(admin))

    assert response.status_code == 422
    assert await count(sessionmaker, Service) == 0


async def test_nome_curto_na_alteracao_responde_422(sessionmaker, client, admin):
    corte = await create(client, admin)

    response = await update_service(client, admin, corte["id"], {"name": "  "})

    assert response.status_code == 422
    assert (await service_in_db(sessionmaker, corte["id"])).name == "Corte"


async def test_nome_e_gravado_sem_os_espacos_das_pontas(sessionmaker, client, admin):
    body = await create(client, admin, "  Corte Degradê  ")
    await update_service(client, admin, body["id"], {"name": "  Degradê  "})

    assert (await service_in_db(sessionmaker, body["id"])).name == "Degradê"


async def test_nome_repetido_com_outra_caixa_responde_400(sessionmaker, client, admin):
    await create(client, admin, "Corte")

    response = await client.post(URL, json={"name": " corte ", "price": 50, "duration_minutes": 45}, headers=auth(admin))

    assert response.status_code == 400
    assert response.json()["detail"] == "Já existe um serviço com o nome 'corte'"
    assert await count(sessionmaker, Service) == 1


async def test_renomear_para_outro_nome_com_outra_caixa_responde_400(sessionmaker, client, admin):
    await create(client, admin, "Corte")
    barba = await create(client, admin, "Barba")

    response = await update_service(client, admin, barba["id"], {"name": "CORTE"})

    assert response.status_code == 400
    assert (await service_in_db(sessionmaker, barba["id"])).name == "Barba"


async def test_mudar_so_a_caixa_do_proprio_nome_e_aceito(sessionmaker, client, admin):
    corte = await create(client, admin, "corte degradê")

    response = await update_service(client, admin, corte["id"], {"name": "Corte Degradê"})

    assert response.status_code == 200
    assert (await service_in_db(sessionmaker, corte["id"])).name == "Corte Degradê"


async def test_nome_de_desativado_sugere_reativar(sessionmaker, client, admin):
    antigo = await create(client, admin, "Corte")
    await deactivate(client, admin, antigo["id"])

    response = await client.post(URL, json={"name": "Corte", "price": 50, "duration_minutes": 45}, headers=auth(admin))

    assert response.status_code == 400
    assert response.json()["detail"] == REACTIVATE


# ── reativação ──────────────────────────────────────────


async def test_reativar_traz_o_servico_de_volta_com_os_vinculos(sessionmaker, client, admin):
    corte = await create(client, admin, "Corte")
    joao = await add_barber(sessionmaker, "joao@teste.com")
    await link(client, admin, corte["id"], joao.id)
    await deactivate(client, admin, corte["id"])
    assert await names(client) == []

    response = await update_service(client, admin, corte["id"], {"is_active": True})

    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert await names(client) == ["Corte"]
    assert await barber_ids(client, corte["id"]) == {str(joao.id)}
    assert await names(client, f"{URL}/barber/{joao.id}") == ["Corte"]


async def test_is_active_false_desativa_como_o_delete(sessionmaker, client, admin):
    corte = await create(client, admin)

    response = await update_service(client, admin, corte["id"], {"is_active": False})

    assert response.status_code == 200
    assert (await service_in_db(sessionmaker, corte["id"])).is_active is False
    assert (await client.get(f"{URL}/{corte['id']}")).status_code == 404


async def test_reativar_e_mudar_o_preco_juntos(sessionmaker, client, admin):
    corte = await create(client, admin)
    await deactivate(client, admin, corte["id"])

    await update_service(client, admin, corte["id"], {"is_active": True, "price": 55})

    assert stored_fields(await service_in_db(sessionmaker, corte["id"])) == ("Corte", Decimal("55.00"), 30, True)


# ── listagem do admin ───────────────────────────────────


async def test_listagem_do_admin_traz_ativos_e_desativados(sessionmaker, client, admin):
    await create(client, admin, "Corte")
    barba = await create(client, admin, "Barba")
    await create(client, admin, "Alisamento")
    await deactivate(client, admin, barba["id"])

    response = await client.get(f"{URL}/admin", headers=auth(admin))

    assert response.status_code == 200
    assert [(s["name"], s["is_active"]) for s in response.json()] == [
        ("Alisamento", True),
        ("Barba", False),
        ("Corte", True),
    ]
    assert await names(client) == ["Alisamento", "Corte"]


@pytest.mark.parametrize("who", ["sem-token", "cliente", "barbeiro"])
async def test_listagem_do_admin_recusa_os_outros(sessionmaker, client, who):
    headers = {}
    if who == "cliente":
        headers = auth(await add_user(sessionmaker, "cliente@teste.com"))
    elif who == "barbeiro":
        headers = auth(await add_user(sessionmaker, "barbeiro@teste.com", UserRole.BARBER))

    response = await client.get(f"{URL}/admin", headers=headers)

    assert response.status_code == 403


# ── vínculos só com ativos ──────────────────────────────


async def test_vincular_servico_desativado_responde_400(sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")
    await deactivate(client, admin, corte["id"])

    response = await link(client, admin, corte["id"], joao.id)

    assert response.status_code == 400
    assert response.json()["detail"] == "Serviço desativado não pode receber barbeiros."
    assert await count(sessionmaker, BarberServiceAssociation) == 0


@pytest.mark.parametrize("inactive", ["perfil", "conta"])
async def test_vincular_barbeiro_desativado_responde_400(sessionmaker, client, admin, inactive):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")
    async with sessionmaker() as db:
        if inactive == "perfil":
            await db.execute(update(Barber).where(Barber.id == joao.id).values(is_active=False))
        else:
            await db.execute(update(User).where(User.id == joao.user_id).values(is_active=False))
        await db.commit()

    response = await link(client, admin, corte["id"], joao.id)

    assert response.status_code == 400
    assert response.json()["detail"] == "Barbeiro desativado não pode ser vinculado."
    assert await count(sessionmaker, BarberServiceAssociation) == 0


async def test_desvincular_servico_desativado_continua_liberado(sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")
    await link(client, admin, corte["id"], joao.id)
    await deactivate(client, admin, corte["id"])

    response = await client.delete(f"{URL}/{corte['id']}/barbers/{joao.id}", headers=auth(admin))

    assert response.status_code == 204
    assert await count(sessionmaker, BarberServiceAssociation) == 0
