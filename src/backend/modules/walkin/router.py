"""
Trim — Walk-in Router

Endpoints de fila de espera.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_barber_or_admin
from src.backend.modules.auth.models import User
from src.backend.modules.walkin.schemas import (
    WalkInAssignRequest,
    WalkInCreateRequest,
    WalkInLiveResponse,
    WalkInResponse,
)
from src.backend.modules.walkin.service import WalkInService

router = APIRouter()

# ── Endpoints Públicos (Display TV) ──────────────────────

@router.get("/live", response_model=list[WalkInLiveResponse])
async def get_live_queue(db: AsyncSession = Depends(get_db)):
    """(Público) Retorna a lista de quem está esperando hoje (nomes mascarados)."""
    service = WalkInService(db)
    queue = await service.list_live_queue()
    
    # Mascarar o nome para privacidade na TV (João Silva -> Joã***)
    response = []
    for item in queue:
        name_parts = item.customer_name.split()
        first_name = name_parts[0]
        masked = first_name[:3] + "***" if len(first_name) >= 3 else first_name + "***"
        
        response.append(WalkInLiveResponse(
            customer_name_masked=masked,
            position=item.position,
            joined_at=item.joined_at
        ))
    return response


# ── Endpoints Autenticados (Recepção / Barbeiros) ────────

@router.post("", response_model=WalkInResponse, status_code=status.HTTP_201_CREATED)
async def add_to_queue(
    data: WalkInCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_barber_or_admin)
):
    """Adiciona um cliente na fila."""
    service = WalkInService(db)
    return await service.add_to_queue(data)


@router.put("/{walkin_id}/assign", response_model=WalkInResponse)
async def assign_to_barber(
    walkin_id: uuid.UUID,
    data: WalkInAssignRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_barber_or_admin)
):
    """Inicia o atendimento (vira Appointment)."""
    service = WalkInService(db)
    try:
        return await service.assign_to_barber(walkin_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{walkin_id}/cancel", response_model=WalkInResponse)
async def cancel_walkin(
    walkin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_barber_or_admin)
):
    """Cancela a entrada na fila."""
    service = WalkInService(db)
    try:
        return await service.cancel_walkin(walkin_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
