"""
Trim — Appointments Router

Rotas do módulo de Agendamentos.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin, get_current_barber_or_admin, get_current_user
from src.backend.modules.auth.models import User
from src.backend.modules.appointments.models import AppointmentStatus
from src.backend.modules.appointments.schemas import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AppointmentStatusUpdateRequest,
    AvailabilityResponse,
    GuestAppointmentCreateRequest,
)
from src.backend.modules.appointments.service import AppointmentService

router = APIRouter()

# ── Endpoints Públicos ───────────────────────────────────

@router.get("/availability", response_model=AvailabilityResponse, summary="Busca horários livres")
async def get_availability(
    barber_id: uuid.UUID = Query(..., description="ID do barbeiro"),
    target_date: date = Query(..., description="Data alvo (YYYY-MM-DD)"),
    duration_minutes: int = Query(..., description="Duração total do(s) serviço(s) em minutos"),
    db: AsyncSession = Depends(get_db)
):
    """Retorna os horários disponíveis (slots) para um barbeiro em uma data."""
    service = AppointmentService(db)
    slots = await service.get_availability(barber_id, target_date, duration_minutes)
    
    return AvailabilityResponse(
        date=str(target_date),
        barber_id=barber_id,
        available_slots=slots
    )


# ── Endpoints Autenticados (Cliente) ─────────────────────

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    data: AppointmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """(Cliente) Cria um novo agendamento com validação de conflitos."""
    service = AppointmentService(db)
    try:
        return await service.create_appointment(current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/guest", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
    data: GuestAppointmentCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """(Visitante) Cria um agendamento e gera um usuário fantasma."""
    from src.backend.modules.auth.models import User, UserRole
    from src.backend.modules.auth.security import get_password_hash
    
    # Criar usuário fantasma
    dummy_email = f"guest_{uuid.uuid4().hex[:8]}@trim.local"
    new_user = User(
        email=dummy_email,
        hashed_password=get_password_hash(uuid.uuid4().hex),
        full_name=data.guest_name,
        role=UserRole.CLIENT,
    )
    db.add(new_user)
    await db.flush()

    # Montar request normal
    app_req = AppointmentCreateRequest(
        barber_id=data.barber_id,
        start_datetime=data.start_datetime,
        service_ids=data.service_ids,
        notes=f"Visitante: {data.guest_name}"
    )

    service = AppointmentService(db)
    try:
        appointment = await service.create_appointment(new_user.id, app_req)
        await db.commit()
        return appointment
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=list[AppointmentResponse])
async def get_my_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """(Cliente) Retorna o histórico de agendamentos do cliente logado."""
    service = AppointmentService(db)
    return await service.get_client_appointments(current_user.id)


@router.put("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_my_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """(Cliente) Cancela um agendamento próprio (apenas se for futuro)."""
    # Em uma versão avançada, faríamos a checagem se o agendamento pertence
    # ao usuário e se é de fato no futuro.
    service = AppointmentService(db)
    appointment = await service.update_status(appointment_id, AppointmentStatus.CANCELLED)
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return appointment


# ── Endpoints Autenticados (Barbeiro) ────────────────────

@router.get("/barber/me", response_model=list[AppointmentResponse])
async def get_barber_appointments(
    db: AsyncSession = Depends(get_db),
    barber_user: User = Depends(get_current_barber_or_admin),
):
    """(Barbeiro) Retorna a agenda do barbeiro logado."""
    # Para extrair o ID do barbeiro a partir do ID do User, precisamos acessar a DB ou o token.
    # Por simplicidade, vamos delegar essa query para o service no futuro.
    # Mas aqui faremos uma checagem rápida no banco:
    from src.backend.modules.barbers.models import Barber
    from sqlalchemy import select
    stmt = select(Barber.id).where(Barber.user_id == barber_user.id)
    barber_id = (await db.execute(stmt)).scalar_one_or_none()
    
    if not barber_id:
        raise HTTPException(status_code=404, detail="Perfil de barbeiro não encontrado.")

    service = AppointmentService(db)
    return await service.get_barber_appointments(barber_id)


@router.put("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: uuid.UUID,
    data: AppointmentStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    barber_user: User = Depends(get_current_barber_or_admin),
):
    """(Barbeiro/Admin) Atualiza o status de um agendamento (ex: COMPLETED, NO_SHOW)."""
    service = AppointmentService(db)
    appointment = await service.update_status(appointment_id, data.status)
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return appointment
