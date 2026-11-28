"""
Testes de integração do módulo de barbeiros (#3).

Spec: SPEC/2026-11-21-testes-integracao-barbers.md

Usam a API de verdade (`client`) e o PostgreSQL de TEST_DATABASE_URL (`sessionmaker`), com um
schema novo a cada teste. Substituem o tests/test_barbers.py gerado, que não importava a aplicação.
"""

import uuid
from datetime import time
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select, update

from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber, WorkSchedule
from tests.agenda_fixtures import needs_db
from tests.api_helpers import add_user, auth

pytestmark = [pytest.mark.asyncio, needs_db]

URL = "/api/barbers"
WEEKDAY = {"start_time": "09:00:00", "end_time": "18:00:00", "break_start": "12:00:00", "break_end": "13:00:00"}


# ── apoio ───────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin(sessionmaker):
    return await add_user(sessionmaker, "dono@teste.com", UserRole.ADMIN, full_name="Dono")


async def create_barber(client, admin, user, **fields):
    response = await client.post(URL, json={"user_id": str(user.id), **fields}, headers=auth(admin))
    assert response.status_code == 201, response.text
    return response.json()


async def new_barber(maker, client, admin, email="joao@teste.com", **fields):
    """Cadastra um barbeiro pela API e devolve (usuário, resposta do cadastro)."""
    user = await add_user(maker, email, full_name=email.split("@")[0].capitalize())
    return user, await create_barber(client, admin, user, **fields)


async def user_role(maker, user_id):
    async with maker() as db:
        return (await db.execute(select(User.role).where(User.id == user_id))).scalar_one()


async def schedules_in_db(maker, barber_id):
    async with maker() as db:
        stmt = select(WorkSchedule).where(WorkSchedule.barber_id == uuid.UUID(barber_id))
        return sorted((await db.execute(stmt)).scalars(), key=lambda s: s.day_of_week)


async def barber_in_db(maker, barber_id):
    async with maker() as db:
        return await db.get(Barber, uuid.UUID(barber_id))


async def deactivate(maker, model, row_id):
    async with maker() as db:
        await db.execute(update(model).where(model.id == row_id).values(is_active=False))
        await db.commit()


async def schedule_of(client, barber_id, day):
    response = await client.get(f"{URL}/{barber_id}/schedule")
    return next(s for s in response.json() if s["day_of_week"] == day)


def day_payload(day, **changes):
    return {"day_of_week": day, **WEEKDAY, "is_working": True, **changes}


# ── listagem pública ────────────────────────────────────


async def test_listagem_sem_barbeiros_e_vazia(sessionmaker, client):
    response = await client.get(URL)

    assert response.status_code == 200
    assert response.json() == []


async def test_listagem_mostra_dados_publicos_sem_comissao(sessionmaker, client, admin):
    user = await add_user(sessionmaker, "joao@teste.com", full_name="João Silva", avatar_url="https://img/joao.png")
    created = await create_barber(
        client, admin, user, bio="Degradê e navalha", instagram_url="https://instagram.com/joao", commission_rate=40
    )

    response = await client.get(URL)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": created["id"],
            "user_id": str(user.id),
            "full_name": "João Silva",
            "avatar_url": "https://img/joao.png",
            "bio": "Degradê e navalha",
            "instagram_url": "https://instagram.com/joao",
        }
    ]


async def test_listagem_esconde_barbeiro_desativado_e_conta_desativada(sessionmaker, client, admin):
    _, ativo = await new_barber(sessionmaker, client, admin, "ativo@teste.com")
    _, perfil_off = await new_barber(sessionmaker, client, admin, "perfiloff@teste.com")
    conta_off_user, _ = await new_barber(sessionmaker, client, admin, "contaoff@teste.com")
    await deactivate(sessionmaker, Barber, uuid.UUID(perfil_off["id"]))
    await deactivate(sessionmaker, User, conta_off_user.id)

    response = await client.get(URL)

    assert [b["id"] for b in response.json()] == [ativo["id"]]


async def test_listagem_nao_inclui_usuarios_sem_perfil_de_barbeiro(sessionmaker, client, admin):
    await add_user(sessionmaker, "barbeiro-sem-perfil@teste.com", UserRole.BARBER)
    _, created = await new_barber(sessionmaker, client, admin)

    response = await client.get(URL)

    assert [b["id"] for b in response.json()] == [created["id"]]


# ── detalhes públicos ───────────────────────────────────


async def test_detalhes_juntam_dados_do_usuario_e_do_barbeiro(sessionmaker, client, admin):
    user = await add_user(sessionmaker, "joao@teste.com", full_name="João Silva", avatar_url="https://img/joao.png")
    created = await create_barber(client, admin, user, bio="Barba e cabelo")

    response = await client.get(f"{URL}/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": created["id"],
        "user_id": str(user.id),
        "full_name": "João Silva",
        "avatar_url": "https://img/joao.png",
        "bio": "Barba e cabelo",
        "instagram_url": None,
        "services": [],  # SPEC/2026-11-23-barbeiros-admin-escala.md: os serviços ativos do barbeiro
    }
    assert "commission_rate" not in body


async def test_detalhes_de_barbeiro_desconhecido_responde_404(sessionmaker, client):
    response = await client.get(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Barbeiro não encontrado."


@pytest.mark.parametrize("what", ["perfil", "conta"])
async def test_detalhes_de_barbeiro_desativado_responde_404(what, sessionmaker, client, admin):
    user, created = await new_barber(sessionmaker, client, admin)
    if what == "perfil":
        await deactivate(sessionmaker, Barber, uuid.UUID(created["id"]))
    else:
        await deactivate(sessionmaker, User, user.id)

    response = await client.get(f"{URL}/{created['id']}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Barbeiro não está ativo."


async def test_detalhes_com_id_que_nao_e_uuid_responde_422(sessionmaker, client):
    response = await client.get(f"{URL}/nao-e-uuid")

    assert response.status_code == 422


# ── escala pública ──────────────────────────────────────


async def test_escala_publica_tem_os_sete_dias_em_ordem(sessionmaker, client, admin):
    _, created = await new_barber(sessionmaker, client, admin)

    response = await client.get(f"{URL}/{created['id']}/schedule")

    assert response.status_code == 200
    days = response.json()
    assert [d["day_of_week"] for d in days] == list(range(7))
    assert all(d["barber_id"] == created["id"] for d in days)
    assert len({d["id"] for d in days}) == 7


async def test_escala_de_barbeiro_desconhecido_responde_404(sessionmaker, client):
    response = await client.get(f"{URL}/{uuid.uuid4()}/schedule")

    assert response.status_code == 404
    assert response.json()["detail"] == "Escala não encontrada."


# ── cadastro pelo admin ─────────────────────────────────


async def test_cadastro_promove_cliente_e_usa_comissao_padrao(sessionmaker, client, admin):
    user = await add_user(sessionmaker, "joao@teste.com")

    response = await client.post(URL, json={"user_id": str(user.id)}, headers=auth(admin))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_id"] == str(user.id)
    assert Decimal(str(body["commission_rate"])) == Decimal("50")
    assert body["is_active"] is True
    assert body["bio"] is None and body["instagram_url"] is None
    assert await user_role(sessionmaker, user.id) == UserRole.BARBER
    stored = await barber_in_db(sessionmaker, body["id"])
    assert stored.user_id == user.id
    assert stored.commission_rate == Decimal("50.00")


async def test_cadastro_grava_comissao_bio_e_instagram_enviados(sessionmaker, client, admin):
    _, body = await new_barber(
        sessionmaker, client, admin, bio="Especialista em barba", instagram_url="https://instagram.com/joao",
        commission_rate=35.5,
    )

    assert Decimal(str(body["commission_rate"])) == Decimal("35.5")
    stored = await barber_in_db(sessionmaker, body["id"])
    assert stored.bio == "Especialista em barba"
    assert stored.instagram_url == "https://instagram.com/joao"
    assert stored.commission_rate == Decimal("35.50")


@pytest.mark.parametrize("commission", [0, 100])
async def test_cadastro_aceita_comissao_nos_limites(commission, sessionmaker, client, admin):
    _, body = await new_barber(sessionmaker, client, admin, commission_rate=commission)

    assert Decimal(str(body["commission_rate"])) == Decimal(commission)


async def test_cadastro_cria_escala_padrao(sessionmaker, client, admin):
    _, body = await new_barber(sessionmaker, client, admin)

    schedules = await schedules_in_db(sessionmaker, body["id"])
    assert [s.day_of_week for s in schedules] == list(range(7))
    domingo, *semana = schedules
    assert domingo.is_working is False
    assert domingo.break_start is None and domingo.break_end is None
    for day in semana:
        assert day.is_working is True
        assert (day.start_time, day.end_time) == (time(9), time(18))
        assert (day.break_start, day.break_end) == (time(12), time(13))


async def test_admin_que_vira_barbeiro_continua_admin(sessionmaker, client, admin):
    body = await create_barber(client, admin, admin)

    assert body["user_id"] == str(admin.id)
    assert await user_role(sessionmaker, admin.id) == UserRole.ADMIN


async def test_barbeiro_cadastrado_aparece_na_listagem_publica(sessionmaker, client, admin):
    _, body = await new_barber(sessionmaker, client, admin)

    response = await client.get(URL)

    assert [b["id"] for b in response.json()] == [body["id"]]


async def test_cadastro_de_usuario_desconhecido_responde_400(sessionmaker, client, admin):
    response = await client.post(URL, json={"user_id": str(uuid.uuid4())}, headers=auth(admin))

    assert response.status_code == 400
    assert response.json()["detail"] == "Usuário não encontrado."
    async with sessionmaker() as db:
        assert (await db.execute(select(func.count()).select_from(Barber))).scalar_one() == 0


async def test_cadastro_repetido_responde_400_sem_duplicar_a_escala(sessionmaker, client, admin):
    user, body = await new_barber(sessionmaker, client, admin)

    response = await client.post(URL, json={"user_id": str(user.id), "bio": "outra"}, headers=auth(admin))

    assert response.status_code == 400
    assert response.json()["detail"] == "Usuário já possui perfil de barbeiro."
    assert len(await schedules_in_db(sessionmaker, body["id"])) == 7
    assert (await barber_in_db(sessionmaker, body["id"])).bio is None


@pytest.mark.parametrize(
    "fields",
    [
        {"commission_rate": 100.01},
        {"commission_rate": -1},
        {"bio": "x" * 501},
        {"instagram_url": "nao-e-url"},
        {"user_id": "nao-e-uuid"},
    ],
    ids=["comissao-acima-de-100", "comissao-negativa", "bio-longa", "instagram-invalido", "user-id-invalido"],
)
async def test_cadastro_com_dados_invalidos_responde_422(fields, sessionmaker, client, admin):
    user = await add_user(sessionmaker, "joao@teste.com")

    response = await client.post(URL, json={"user_id": str(user.id), **fields}, headers=auth(admin))

    assert response.status_code == 422
    assert await user_role(sessionmaker, user.id) == UserRole.CLIENT


async def test_cadastro_aceita_bio_de_500_caracteres(sessionmaker, client, admin):
    _, body = await new_barber(sessionmaker, client, admin, bio="x" * 500)

    assert len(body["bio"]) == 500


# ── alteração da escala pelo admin ──────────────────────


async def test_admin_altera_um_dia_da_escala(sessionmaker, client, admin):
    _, body = await new_barber(sessionmaker, client, admin)
    terca = await schedule_of(client, body["id"], 2)
    payload = day_payload(2, start_time="10:00:00", end_time="20:00:00", break_start="14:00:00", break_end="15:00:00")

    response = await client.put(f"{URL}/{body['id']}/schedule/{terca['id']}", json=payload, headers=auth(admin))

    assert response.status_code == 200, response.text
    assert response.json() == {**payload, "id": terca["id"], "barber_id": body["id"]}
    stored = {s.day_of_week: s for s in await schedules_in_db(sessionmaker, body["id"])}
    assert (stored[2].start_time, stored[2].end_time) == (time(10), time(20))
    assert (stored[2].break_start, stored[2].break_end) == (time(14), time(15))
    assert (stored[3].start_time, stored[3].end_time) == (time(9), time(18))


async def test_admin_marca_folga_e_tira_o_almoco(sessionmaker, client, admin):
    _, body = await new_barber(sessionmaker, client, admin)
    sabado = await schedule_of(client, body["id"], 6)
    payload = day_payload(6, is_working=False, break_start=None, break_end=None)

    response = await client.put(f"{URL}/{body['id']}/schedule/{sabado['id']}", json=payload, headers=auth(admin))

    assert response.status_code == 200, response.text
    publico = await schedule_of(client, body["id"], 6)
    assert publico["is_working"] is False
    assert publico["break_start"] is None and publico["break_end"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"start_time": "18:00:00", "end_time": "09:00:00"},
        {"start_time": "09:00:00", "end_time": "09:00:00"},
        {"break_start": "13:00:00", "break_end": "12:00:00"},
        {"day_of_week": 7},
        {"day_of_week": -1},
    ],
    ids=["fim-antes-do-inicio", "fim-igual-ao-inicio", "almoco-invertido", "dia-7", "dia-negativo"],
)
async def test_escala_invalida_responde_422_sem_mudar_o_dia(changes, sessionmaker, client, admin):
    _, body = await new_barber(sessionmaker, client, admin)
    segunda = await schedule_of(client, body["id"], 1)

    response = await client.put(
        f"{URL}/{body['id']}/schedule/{segunda['id']}", json=day_payload(1, **changes), headers=auth(admin)
    )

    assert response.status_code == 422
    assert await schedule_of(client, body["id"], 1) == segunda


async def test_dia_de_escala_de_outro_barbeiro_responde_404(sessionmaker, client, admin):
    _, joao = await new_barber(sessionmaker, client, admin, "joao@teste.com")
    _, pedro = await new_barber(sessionmaker, client, admin, "pedro@teste.com")
    dia_do_pedro = await schedule_of(client, pedro["id"], 1)

    response = await client.put(
        f"{URL}/{joao['id']}/schedule/{dia_do_pedro['id']}", json=day_payload(1, start_time="07:00:00"),
        headers=auth(admin),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dia de escala não encontrado."
    assert await schedule_of(client, pedro["id"], 1) == dia_do_pedro


async def test_dia_de_escala_desconhecido_responde_404(sessionmaker, client, admin):
    _, body = await new_barber(sessionmaker, client, admin)

    response = await client.put(f"{URL}/{body['id']}/schedule/{uuid.uuid4()}", json=day_payload(1), headers=auth(admin))

    assert response.status_code == 404


# ── bio pelo próprio barbeiro ───────────────────────────


async def test_barbeiro_altera_a_propria_bio_e_instagram(sessionmaker, client, admin):
    user, body = await new_barber(sessionmaker, client, admin, commission_rate=40)
    barbeiro = await reload_user(sessionmaker, user)

    response = await client.put(
        f"{URL}/me/bio", json={"bio": "Nova bio", "instagram_url": "https://instagram.com/novo"}, headers=auth(barbeiro)
    )

    assert response.status_code == 200, response.text
    assert response.json()["bio"] == "Nova bio"
    assert response.json()["instagram_url"] == "https://instagram.com/novo"
    publico = (await client.get(f"{URL}/{body['id']}")).json()
    assert publico["bio"] == "Nova bio"
    assert publico["instagram_url"] == "https://instagram.com/novo"


async def test_campo_nao_enviado_continua_como_estava(sessionmaker, client, admin):
    user, body = await new_barber(sessionmaker, client, admin, bio="Antiga", instagram_url="https://instagram.com/joao")
    barbeiro = await reload_user(sessionmaker, user)

    response = await client.put(f"{URL}/me/bio", json={"bio": "Nova"}, headers=auth(barbeiro))

    assert response.status_code == 200
    stored = await barber_in_db(sessionmaker, body["id"])
    assert stored.bio == "Nova"
    assert stored.instagram_url == "https://instagram.com/joao"


async def test_barbeiro_nao_consegue_mudar_a_propria_comissao(sessionmaker, client, admin):
    user, body = await new_barber(sessionmaker, client, admin, commission_rate=40)
    barbeiro = await reload_user(sessionmaker, user)

    response = await client.put(
        f"{URL}/me/bio", json={"bio": "Nova", "commission_rate": 90}, headers=auth(barbeiro)
    )

    assert response.status_code == 200
    assert (await barber_in_db(sessionmaker, body["id"])).commission_rate == Decimal("40.00")


async def test_bio_de_usuario_sem_cadastro_de_barbeiro_responde_404(sessionmaker, client):
    sem_perfil = await add_user(sessionmaker, "sem-perfil@teste.com", UserRole.BARBER)

    response = await client.put(f"{URL}/me/bio", json={"bio": "Oi"}, headers=auth(sem_perfil))

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfil de barbeiro não encontrado."


async def test_bio_longa_responde_422(sessionmaker, client, admin):
    user, body = await new_barber(sessionmaker, client, admin, bio="Antiga")
    barbeiro = await reload_user(sessionmaker, user)

    response = await client.put(f"{URL}/me/bio", json={"bio": "x" * 501}, headers=auth(barbeiro))

    assert response.status_code == 422
    assert (await barber_in_db(sessionmaker, body["id"])).bio == "Antiga"


async def reload_user(maker, user):
    """Relê o usuário do banco, já com o perfil `barber` que o cadastro deu a ele."""
    async with maker() as db:
        return await db.get(User, user.id)


# ── permissões ──────────────────────────────────────────


async def test_rotas_protegidas_sem_token_respondem_403(sessionmaker, client, admin):
    user, body = await new_barber(sessionmaker, client, admin)
    dia = await schedule_of(client, body["id"], 1)

    responses = [
        await client.post(URL, json={"user_id": str(user.id)}),
        await client.put(f"{URL}/{body['id']}/schedule/{dia['id']}", json=day_payload(1)),
        await client.put(f"{URL}/me/bio", json={"bio": "Oi"}),
    ]

    assert [r.status_code for r in responses] == [403, 403, 403]


@pytest.mark.parametrize("role", [UserRole.CLIENT, UserRole.BARBER])
async def test_so_admin_cadastra_barbeiro(role, sessionmaker, client):
    outro = await add_user(sessionmaker, "outro@teste.com", role)
    alvo = await add_user(sessionmaker, "alvo@teste.com")

    response = await client.post(URL, json={"user_id": str(alvo.id)}, headers=auth(outro))

    assert response.status_code == 403
    assert await user_role(sessionmaker, alvo.id) == UserRole.CLIENT


async def test_barbeiro_nao_altera_a_propria_escala(sessionmaker, client, admin):
    user, body = await new_barber(sessionmaker, client, admin)
    barbeiro = await reload_user(sessionmaker, user)
    dia = await schedule_of(client, body["id"], 1)

    response = await client.put(
        f"{URL}/{body['id']}/schedule/{dia['id']}", json=day_payload(1, start_time="06:00:00"), headers=auth(barbeiro)
    )

    assert response.status_code == 403
    assert await schedule_of(client, body["id"], 1) == dia


async def test_cliente_nao_altera_bio(sessionmaker, client):
    cliente = await add_user(sessionmaker, "cliente@teste.com")

    response = await client.put(f"{URL}/me/bio", json={"bio": "Oi"}, headers=auth(cliente))

    assert response.status_code == 403
