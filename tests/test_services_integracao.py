"""
Testes de integração do catálogo de serviços (#3).

Spec: SPEC/2026-11-21-testes-integracao-services.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Substituem o tests/test_services.py gerado, que não importava a aplicação.
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select, update

from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber
from src.backend.modules.services.models import BarberServiceAssociation, Service
from tests.agenda_fixtures import needs_db
from tests.api_helpers import add_barber, add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/services"
LINK_ERROR = "Não foi possível vincular. Verifique se o barbeiro/serviço existem ou se já estão vinculados."


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN)


async def create(client, admin, name="Corte", price=40, duration=30, **extra):
    response = await client.post(
        URL, json={"name": name, "price": price, "duration_minutes": duration, **extra}, headers=auth(admin)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def link(client, admin, service_id, barber_id):
    return await client.post(f"{URL}/{service_id}/barbers/{barber_id}", headers=auth(admin))


async def service_in_db(maker, service_id):
    async with maker() as db:
        return await db.get(Service, uuid.UUID(str(service_id)))


async def count(maker, model):
    async with maker() as db:
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()


async def names(client, url=URL):
    response = await client.get(url)
    assert response.status_code == 200, response.text
    return [s["name"] for s in response.json()]


async def barber_ids(client, service_id):
    response = await client.get(f"{URL}/{service_id}")
    assert response.status_code == 200, response.text
    return {b["id"] for b in response.json()["barbers"]}


# ── listagem pública ────────────────────────────────────


async def test_listagem_sem_servicos_e_vazia(sessionmaker, client):
    response = await client.get(URL)

    assert response.status_code == 200
    assert response.json() == []


async def test_listagem_mostra_os_dados_do_servico(sessionmaker, client, admin):
    created = await create(client, admin, "Barba", 25.5, 20, description="Toalha quente e navalha")

    (listed,) = (await client.get(URL)).json()

    assert listed == created
    assert listed["name"] == "Barba"
    assert listed["description"] == "Toalha quente e navalha"
    assert Decimal(listed["price"]) == Decimal("25.50")
    assert listed["duration_minutes"] == 20
    assert listed["is_active"] is True


async def test_listagem_em_ordem_alfabetica_sem_os_desativados(sessionmaker, client, admin):
    await create(client, admin, "Sobrancelha")
    barba = await create(client, admin, "Barba")
    await create(client, admin, "Corte")
    await create(client, admin, "Pigmentação")
    await client.delete(f"{URL}/{barba['id']}", headers=auth(admin))

    assert await names(client) == ["Corte", "Pigmentação", "Sobrancelha"]


# ── detalhes públicos ───────────────────────────────────


async def test_detalhes_trazem_os_barbeiros_vinculados_sem_comissao(sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com", full_name="João", commission_rate=40)
    await add_barber(sessionmaker, "pedro@teste.com")
    await link(client, admin, corte["id"], joao.id)

    response = await client.get(f"{URL}/{corte['id']}")

    assert response.status_code == 200
    body = response.json()
    assert {k: body[k] for k in corte} == corte
    assert body["barbers"] == [
        {
            "id": str(joao.id),
            "user_id": str(joao.user_id),
            "full_name": "João",
            "avatar_url": None,
            "bio": None,
            "instagram_url": None,
        }
    ]


async def test_detalhes_sem_barbeiros_vinculados(sessionmaker, client, admin):
    corte = await create(client, admin)

    assert await barber_ids(client, corte["id"]) == set()


async def test_detalhes_escondem_barbeiro_desativado_e_conta_desativada(sessionmaker, client, admin):
    corte = await create(client, admin)
    ativo = await add_barber(sessionmaker, "ativo@teste.com")
    perfil_off = await add_barber(sessionmaker, "perfiloff@teste.com")
    conta_off = await add_barber(sessionmaker, "contaoff@teste.com")
    for barber in (ativo, perfil_off, conta_off):
        assert (await link(client, admin, corte["id"], barber.id)).status_code == 201
    # Desativados depois do vínculo: vincular quem já está inativo é recusado (#39).
    async with sessionmaker() as db:
        await db.execute(update(Barber).where(Barber.id == perfil_off.id).values(is_active=False))
        await db.execute(update(User).where(User.id == conta_off.user_id).values(is_active=False))
        await db.commit()

    assert await barber_ids(client, corte["id"]) == {str(ativo.id)}


async def test_detalhes_de_servico_desconhecido_respondem_404(sessionmaker, client):
    response = await client.get(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Serviço não encontrado ou inativo."


async def test_detalhes_de_servico_desativado_respondem_404(sessionmaker, client, admin):
    corte = await create(client, admin)
    await client.delete(f"{URL}/{corte['id']}", headers=auth(admin))

    response = await client.get(f"{URL}/{corte['id']}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Serviço não encontrado ou inativo."


# ── serviços de um barbeiro ─────────────────────────────


async def test_servicos_do_barbeiro_em_ordem_alfabetica(sessionmaker, client, admin):
    joao = await add_barber(sessionmaker, "joao@teste.com")
    pedro = await add_barber(sessionmaker, "pedro@teste.com")
    corte, barba, luzes = [await create(client, admin, n) for n in ("Corte", "Barba", "Luzes")]
    for service in (corte, barba):
        await link(client, admin, service["id"], joao.id)
    await link(client, admin, luzes["id"], pedro.id)

    assert await names(client, f"{URL}/barber/{joao.id}") == ["Barba", "Corte"]
    assert await names(client, f"{URL}/barber/{pedro.id}") == ["Luzes"]


async def test_servicos_do_barbeiro_sem_os_desativados(sessionmaker, client, admin):
    joao = await add_barber(sessionmaker, "joao@teste.com")
    corte, barba = await create(client, admin, "Corte"), await create(client, admin, "Barba")
    await link(client, admin, corte["id"], joao.id)
    await link(client, admin, barba["id"], joao.id)
    await client.delete(f"{URL}/{barba['id']}", headers=auth(admin))

    assert await names(client, f"{URL}/barber/{joao.id}") == ["Corte"]


async def test_servicos_de_barbeiro_desconhecido_ou_sem_vinculo_sao_vazios(sessionmaker, client, admin):
    await create(client, admin)
    sem_vinculo = await add_barber(sessionmaker, "joao@teste.com")

    assert await names(client, f"{URL}/barber/{uuid.uuid4()}") == []
    assert await names(client, f"{URL}/barber/{sem_vinculo.id}") == []


# ── criação pelo admin ──────────────────────────────────


async def test_criacao_grava_servico_ativo(sessionmaker, client, admin):
    response = await client.post(
        URL,
        json={"name": "Corte degradê", "description": "Máquina e tesoura", "price": "45.90", "duration_minutes": 40},
        headers=auth(admin),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert uuid.UUID(body["id"])
    assert body["is_active"] is True
    stored = await service_in_db(sessionmaker, body["id"])
    assert stored.name == "Corte degradê"
    assert stored.description == "Máquina e tesoura"
    assert stored.price == Decimal("45.90")
    assert stored.duration_minutes == 40


async def test_criacao_sem_descricao_e_com_preco_zero(sessionmaker, client, admin):
    body = await create(client, admin, "Retoque", 0, 10)

    assert body["description"] is None
    assert Decimal(body["price"]) == Decimal("0")


async def test_preco_e_guardado_com_duas_casas(sessionmaker, client, admin):
    body = await create(client, admin, price="39.999")

    assert (await service_in_db(sessionmaker, body["id"])).price == Decimal("40.00")


async def test_nome_repetido_responde_400(sessionmaker, client, admin):
    await create(client, admin, "Corte")

    response = await client.post(URL, json={"name": "Corte", "price": 50, "duration_minutes": 45}, headers=auth(admin))

    assert response.status_code == 400
    assert response.json()["detail"] == "Já existe um serviço com o nome 'Corte'"
    assert await count(sessionmaker, Service) == 1


async def test_nome_de_servico_desativado_tambem_nao_pode_ser_reusado(sessionmaker, client, admin):
    antigo = await create(client, admin, "Corte")
    await client.delete(f"{URL}/{antigo['id']}", headers=auth(admin))

    response = await client.post(URL, json={"name": "Corte", "price": 50, "duration_minutes": 45}, headers=auth(admin))

    assert response.status_code == 400


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Corte", "price": -0.01, "duration_minutes": 30},
        {"name": "Corte", "price": 40, "duration_minutes": 0},
        {"name": "Corte", "price": 40, "duration_minutes": -15},
        {"name": "x" * 101, "price": 40, "duration_minutes": 30},
        {"price": 40, "duration_minutes": 30},
        {"name": "Corte", "duration_minutes": 30},
        {"name": "Corte", "price": 40},
        {"name": "Corte", "price": "quarenta", "duration_minutes": 30},
    ],
    ids=["preco-negativo", "duracao-zero", "duracao-negativa", "nome-longo", "sem-nome", "sem-preco",
         "sem-duracao", "preco-texto"],
)
async def test_criacao_invalida_responde_422(payload, sessionmaker, client, admin):
    response = await client.post(URL, json=payload, headers=auth(admin))

    assert response.status_code == 422
    assert await count(sessionmaker, Service) == 0


async def test_nome_de_100_caracteres_e_aceito(sessionmaker, client, admin):
    body = await create(client, admin, "x" * 100)

    assert len(body["name"]) == 100


# ── alteração pelo admin ────────────────────────────────


async def test_alteracao_muda_so_os_campos_enviados(sessionmaker, client, admin):
    corte = await create(client, admin, "Corte", 40, 30, description="Simples")

    response = await client.put(f"{URL}/{corte['id']}", json={"price": "55.00"}, headers=auth(admin))

    assert response.status_code == 200, response.text
    stored = await service_in_db(sessionmaker, corte["id"])
    assert stored.price == Decimal("55.00")
    assert (stored.name, stored.duration_minutes, stored.description) == ("Corte", 30, "Simples")


async def test_alteracao_de_todos_os_campos(sessionmaker, client, admin):
    corte = await create(client, admin)
    novo = {"name": "Corte premium", "description": "Com lavagem", "price": "70.00", "duration_minutes": 60}

    response = await client.put(f"{URL}/{corte['id']}", json=novo, headers=auth(admin))

    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["description"], body["duration_minutes"]) == ("Corte premium", "Com lavagem", 60)
    assert Decimal(body["price"]) == Decimal("70.00")
    assert await names(client) == ["Corte premium"]


async def test_alteracao_pode_apagar_a_descricao(sessionmaker, client, admin):
    corte = await create(client, admin, description="Simples")

    await client.put(f"{URL}/{corte['id']}", json={"description": None}, headers=auth(admin))

    assert (await service_in_db(sessionmaker, corte["id"])).description is None


async def test_alteracao_para_nome_de_outro_servico_responde_400(sessionmaker, client, admin):
    await create(client, admin, "Barba")
    corte = await create(client, admin, "Corte")

    response = await client.put(f"{URL}/{corte['id']}", json={"name": "Barba"}, headers=auth(admin))

    assert response.status_code == 400
    assert response.json()["detail"] == "Já existe um serviço com o nome 'Barba'"
    assert (await service_in_db(sessionmaker, corte["id"])).name == "Corte"


async def test_alteracao_mantendo_o_proprio_nome_e_aceita(sessionmaker, client, admin):
    corte = await create(client, admin, "Corte")

    response = await client.put(f"{URL}/{corte['id']}", json={"name": "Corte", "price": 45}, headers=auth(admin))

    assert response.status_code == 200
    assert Decimal(response.json()["price"]) == Decimal("45.00")


async def test_alteracao_de_servico_desconhecido_responde_404(sessionmaker, client, admin):
    response = await client.put(f"{URL}/{uuid.uuid4()}", json={"price": 10}, headers=auth(admin))

    assert response.status_code == 404
    assert response.json()["detail"] == "Serviço não encontrado."


@pytest.mark.parametrize(
    "changes",
    [{"price": -1}, {"duration_minutes": 0}, {"name": "x" * 101}],
    ids=["preco-negativo", "duracao-zero", "nome-longo"],
)
async def test_alteracao_invalida_responde_422(changes, sessionmaker, client, admin):
    corte = await create(client, admin)

    response = await client.put(f"{URL}/{corte['id']}", json=changes, headers=auth(admin))

    assert response.status_code == 422
    stored = await service_in_db(sessionmaker, corte["id"])
    assert (stored.name, stored.price, stored.duration_minutes) == ("Corte", Decimal("40.00"), 30)


# ── desativação pelo admin ──────────────────────────────


async def test_desativacao_e_soft_delete(sessionmaker, client, admin):
    corte = await create(client, admin, price="42.50")

    response = await client.delete(f"{URL}/{corte['id']}", headers=auth(admin))

    assert response.status_code == 204
    assert response.content == b""
    stored = await service_in_db(sessionmaker, corte["id"])
    assert stored.is_active is False
    assert stored.price == Decimal("42.50")
    assert await names(client) == []


async def test_desativacao_mantem_os_vinculos_no_banco(sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")
    await link(client, admin, corte["id"], joao.id)

    await client.delete(f"{URL}/{corte['id']}", headers=auth(admin))

    assert await count(sessionmaker, BarberServiceAssociation) == 1
    assert await names(client, f"{URL}/barber/{joao.id}") == []


async def test_desativacao_de_servico_desconhecido_responde_404(sessionmaker, client, admin):
    response = await client.delete(f"{URL}/{uuid.uuid4()}", headers=auth(admin))

    assert response.status_code == 404
    assert response.json()["detail"] == "Serviço não encontrado."


# ── vínculos com barbeiros ──────────────────────────────


async def test_vinculo_aparece_nas_duas_listas(sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")

    response = await link(client, admin, corte["id"], joao.id)

    assert response.status_code == 201
    assert response.json() == {"message": "Vínculo criado com sucesso."}
    assert await barber_ids(client, corte["id"]) == {str(joao.id)}
    assert await names(client, f"{URL}/barber/{joao.id}") == ["Corte"]


async def test_varios_barbeiros_no_mesmo_servico(sessionmaker, client, admin):
    corte = await create(client, admin)
    barbeiros = [await add_barber(sessionmaker, f"b{i}@teste.com") for i in range(3)]
    for barber in barbeiros:
        await link(client, admin, corte["id"], barber.id)

    assert await barber_ids(client, corte["id"]) == {str(b.id) for b in barbeiros}


async def test_vinculo_repetido_responde_400_sem_duplicar(sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")
    await link(client, admin, corte["id"], joao.id)

    response = await link(client, admin, corte["id"], joao.id)

    assert response.status_code == 400
    assert response.json()["detail"] == LINK_ERROR
    assert await count(sessionmaker, BarberServiceAssociation) == 1


@pytest.mark.parametrize("missing", ["barbeiro", "servico"])
async def test_vinculo_com_barbeiro_ou_servico_desconhecido_responde_400(missing, sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")
    service_id = uuid.uuid4() if missing == "servico" else corte["id"]
    barber_id = uuid.uuid4() if missing == "barbeiro" else joao.id

    response = await link(client, admin, service_id, barber_id)

    assert response.status_code == 400
    assert response.json()["detail"] == LINK_ERROR
    assert await count(sessionmaker, BarberServiceAssociation) == 0


async def test_desvinculo_desfaz_as_duas_listas(sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")
    pedro = await add_barber(sessionmaker, "pedro@teste.com")
    await link(client, admin, corte["id"], joao.id)
    await link(client, admin, corte["id"], pedro.id)

    response = await client.delete(f"{URL}/{corte['id']}/barbers/{joao.id}", headers=auth(admin))

    assert response.status_code == 204
    assert await barber_ids(client, corte["id"]) == {str(pedro.id)}
    assert await names(client, f"{URL}/barber/{joao.id}") == []


async def test_desvinculo_do_que_nao_esta_vinculado_responde_404(sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")

    response = await client.delete(f"{URL}/{corte['id']}/barbers/{joao.id}", headers=auth(admin))

    assert response.status_code == 404
    assert response.json()["detail"] == "Vínculo não encontrado."


async def test_vincular_de_novo_depois_do_desvinculo(sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")
    await link(client, admin, corte["id"], joao.id)
    await client.delete(f"{URL}/{corte['id']}/barbers/{joao.id}", headers=auth(admin))

    response = await link(client, admin, corte["id"], joao.id)

    assert response.status_code == 201
    assert await barber_ids(client, corte["id"]) == {str(joao.id)}


# ── permissões ──────────────────────────────────────────


def admin_requests(service_id, barber_id):
    return [
        ("POST", URL, {"name": "Novo", "price": 10, "duration_minutes": 10}),
        ("PUT", f"{URL}/{service_id}", {"price": 1}),
        ("DELETE", f"{URL}/{service_id}", None),
        ("POST", f"{URL}/{service_id}/barbers/{barber_id}", None),
        ("DELETE", f"{URL}/{service_id}/barbers/{barber_id}", None),
    ]


@pytest.mark.parametrize("who", ["sem-token", "cliente", "barbeiro"])
async def test_rotas_do_admin_recusam_os_outros(who, sessionmaker, client, admin):
    corte = await create(client, admin)
    joao = await add_barber(sessionmaker, "joao@teste.com")
    await link(client, admin, corte["id"], joao.id)
    headers = {}
    if who == "cliente":
        headers = auth(await add_user(sessionmaker, "cliente@teste.com"))
    elif who == "barbeiro":
        headers = auth(await add_user(sessionmaker, "outro@teste.com", UserRole.BARBER))

    statuses = [
        (await client.request(method, url, json=body, headers=headers)).status_code
        for method, url, body in admin_requests(corte["id"], joao.id)
    ]

    assert statuses == [403] * 5
    stored = await service_in_db(sessionmaker, corte["id"])
    assert (stored.is_active, stored.price) == (True, Decimal("40.00"))
    assert await count(sessionmaker, Service) == 1
    assert await count(sessionmaker, BarberServiceAssociation) == 1
