"""
Trim — Finance Router

Endpoints do PDV (Ponto de Venda) e gestão de caixa e comissões.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin, get_current_barber_or_admin
from src.backend.modules.auth.models import User
from src.backend.modules.finance.schemas import (
    AppointmentCheckoutRequest,
    CommissionResponse,
    PayCommissionsRequest,
    ProductCheckoutRequest,
    TransactionResponse,
)
from src.backend.modules.finance.service import FinanceService

router = APIRouter()

# ── PDV / Checkout (Admin) ───────────────────────────────

@router.post("/checkout/appointment/{appointment_id}", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def checkout_appointment(
    appointment_id: uuid.UUID,
    data: AppointmentCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Caixa) Realiza a cobrança de um agendamento e gera comissão do barbeiro."""
    service = FinanceService(db)
    try:
        return await service.checkout_appointment(appointment_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/checkout/product", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def checkout_product(
    data: ProductCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Caixa) Realiza a venda de um produto avulso no balcão e dá baixa no estoque."""
    service = FinanceService(db)
    try:
        return await service.checkout_product(data, admin_user_id=admin.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Extrato de caixa."""
    service = FinanceService(db)
    return await service.list_transactions()


# ── Comissões (Admin e Barbeiros) ────────────────────────

@router.get("/commissions/me", response_model=list[CommissionResponse])
async def get_my_commissions(
    db: AsyncSession = Depends(get_db),
    barber_user: User = Depends(get_current_barber_or_admin)
):
    """(Barbeiro) Vê seu próprio extrato de comissões (pendentes e pagas)."""
    # Descobre o barber_id a partir do user logado
    from src.backend.modules.barbers.models import Barber
    stmt = select(Barber.id).where(Barber.user_id == barber_user.id)
    barber_id = (await db.execute(stmt)).scalar_one_or_none()
    
    if not barber_id:
        raise HTTPException(status_code=404, detail="Perfil de barbeiro não encontrado.")

    service = FinanceService(db)
    return await service.list_commissions_by_barber(barber_id)


@router.get("/commissions/{barber_id}", response_model=list[CommissionResponse])
async def list_barber_commissions(
    barber_id: uuid.UUID,
    only_pending: bool = True,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Vê as comissões de um barbeiro específico."""
    service = FinanceService(db)
    return await service.list_commissions_by_barber(barber_id, only_pending)


@router.put("/commissions/pay", response_model=list[CommissionResponse])
async def pay_commissions(
    data: PayCommissionsRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Marca um lote de comissões como pago (acerto de contas)."""
    service = FinanceService(db)
    try:
        return await service.pay_commissions(data.barber_id, data.commission_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
