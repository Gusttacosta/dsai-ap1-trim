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
    BarberCreateRequest,
    BarberPublicResponse,
    BarberResponse,
    BarberUpdateAdminRequest,
    BarberUpdateSelfRequest,
    WorkScheduleResponse,
    WorkScheduleUpdate,
)
from src.backend.modules.barbers.service import BarberService

router = APIRouter()

# ── Endpoints Públicos ───────────────────────────────────

@router.get("", response_model=list[BarberPublicResponse], summary="Lista barbeiros ativos")
async def list_barbers(db: AsyncSession = Depends(get_db)):
    """Vitrine: retorna os barbeiros e seus dados de perfil público."""
    service = BarberService(db)
    return await service.list_active_barbers()

@router.get("/{barber_id}", response_model=BarberPublicResponse)
async def get_barber(barber_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Detalhes públicos de um barbeiro específico."""
    service = BarberService(db)
    result = await service.get_barber_by_id(barber_id)
    if not result:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado.")
    
    barber, user = result
    if not barber.is_active or not user.is_active:
        raise HTTPException(status_code=404, detail="Barbeiro não está ativo.")

    return BarberPublicResponse(
        id=barber.id,
        user_id=user.id,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=barber.bio,
        instagram_url=barber.instagram_url,
    )

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

@router.put("/{barber_id}/schedule/{schedule_id}", response_model=WorkScheduleResponse)
async def update_schedule(
    barber_id: uuid.UUID,
    schedule_id: uuid.UUID,
    data: WorkScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Modifica um dia específico da escala de trabalho do barbeiro."""
    service = BarberService(db)
    schedule = await service.update_schedule(
        barber_id, schedule_id, data.model_dump(exclude_unset=True)
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Dia de escala não encontrado.")
    return schedule


# ── Endpoints Barbeiro (Self) ────────────────────────────

@router.put("/me/bio", response_model=BarberResponse)
async def update_my_bio(
    data: BarberUpdateSelfRequest,
    db: AsyncSession = Depends(get_db),
    barber_user: User = Depends(get_current_barber_or_admin),
):
    """(Barbeiro) Permite que o próprio barbeiro atualize sua bio e instagram."""
    service = BarberService(db)
    barber = await service.get_barber_by_user_id(barber_user.id)
    
    if not barber:
        raise HTTPException(status_code=404, detail="Perfil de barbeiro não encontrado.")

    if data.bio is not None:
        barber.bio = data.bio
    if data.instagram_url is not None:
        barber.instagram_url = str(data.instagram_url)

    await db.commit()
    await db.refresh(barber)
    return barber
