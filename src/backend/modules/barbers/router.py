"""
Trim — Barbers Router

Rotas do módulo de equipe de barbeiros.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin, get_current_barber_or_admin
from src.backend.modules.auth.models import User
from src.backend.modules.barbers.schemas import (
    BarberAdminResponse,
    BarberCreateRequest,
    BarberDetailResponse,
    BarberPublicResponse,
    BarberResponse,
    BarberSelfResponse,
    BarberUpdateAdminRequest,
    BarberUpdateSelfRequest,
    WorkScheduleDay,
    WorkScheduleResponse,
    WorkScheduleUpdate,
)
from src.backend.modules.barbers.service import BarberService, InvalidSchedule

router = APIRouter()

NOT_FOUND = "Barbeiro não encontrado."

# ── Endpoints Públicos ───────────────────────────────────

@router.get("", response_model=list[BarberPublicResponse], summary="Lista barbeiros ativos")
async def list_barbers(db: AsyncSession = Depends(get_db)):
    """Vitrine: retorna os barbeiros e seus dados de perfil público."""
    service = BarberService(db)
    return await service.list_active_barbers()


@router.get("/admin", response_model=list[BarberAdminResponse], summary="(Admin) Lista todos os barbeiros")
async def list_all_barbers(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Ativos e desativados, com a comissão. Declarada antes de /{barber_id}."""
    return await BarberService(db).list_all_barbers()


@router.get("/{barber_id}", response_model=BarberDetailResponse)
async def get_barber(barber_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Detalhes públicos de um barbeiro, com os serviços ativos que ele faz."""
    service = BarberService(db)
    result = await service.get_barber_by_id(barber_id)
    if not result:
        raise HTTPException(status_code=404, detail=NOT_FOUND)

    detail = await service.get_active_barber_detail(barber_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Barbeiro não está ativo.")
    return detail

@router.get("/{barber_id}/schedule", response_model=list[WorkScheduleResponse])
async def get_barber_schedule(barber_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retorna a escala de trabalho do barbeiro (visão pública para agendamento)."""
    service = BarberService(db)
    schedules = await service.get_schedules(barber_id)
    if not schedules:
        raise HTTPException(status_code=404, detail="Escala não encontrada.")
    return schedules


# ── Endpoints Admin ──────────────────────────────────────

@router.post("", response_model=BarberResponse, status_code=status.HTTP_201_CREATED)
async def create_barber(
    data: BarberCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Promove um usuário a barbeiro e gera a escala padrão."""
    service = BarberService(db)
    try:
        return await service.create_barber(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{barber_id}", response_model=BarberAdminResponse)
async def update_barber(
    barber_id: uuid.UUID,
    data: BarberUpdateAdminRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Altera comissão, bio, Instagram e ativação. Só os campos enviados mudam."""
    try:
        barber = await BarberService(db).update_barber(barber_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not barber:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return barber


@router.put("/{barber_id}/schedule", response_model=list[WorkScheduleResponse])
async def replace_week(
    barber_id: uuid.UUID,
    data: list[WorkScheduleDay],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Grava os 7 dias da escala de uma vez: ou todos, ou nenhum."""
    try:
        week = await BarberService(db).replace_week(barber_id, data)
    except InvalidSchedule as e:
        raise HTTPException(status_code=422, detail=str(e))
    if week is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return week


@router.put("/{barber_id}/schedule/{schedule_id}", response_model=WorkScheduleResponse)
async def update_schedule(
    barber_id: uuid.UUID,
    schedule_id: uuid.UUID,
    data: WorkScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Altera um dia da escala. Só os campos enviados mudam; as regras valem no resultado."""
    service = BarberService(db)
    try:
        schedule = await service.update_schedule(barber_id, schedule_id, data)
    except InvalidSchedule as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not schedule:
        raise HTTPException(status_code=404, detail="Dia de escala não encontrado.")
    return schedule


# ── Endpoints Barbeiro (Self) ────────────────────────────

@router.put("/me/bio", response_model=BarberSelfResponse)
async def update_my_bio(
    data: BarberUpdateSelfRequest,
    db: AsyncSession = Depends(get_db),
    barber_user: User = Depends(get_current_barber_or_admin),
):
    """(Barbeiro) O próprio barbeiro altera a bio e o Instagram. `null` apaga o campo."""
    service = BarberService(db)
    barber = await service.get_barber_by_user_id(barber_user.id)

    if not barber:
        raise HTTPException(status_code=404, detail="Perfil de barbeiro não encontrado.")

    return await service.update_own_profile(barber, data.model_dump(exclude_unset=True))
