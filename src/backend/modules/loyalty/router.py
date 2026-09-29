"""
Trim — Loyalty Router

Endpoints de manipulação de carteira e resgate de pontos.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin, get_current_user
from src.backend.modules.auth.models import User
from src.backend.modules.loyalty.schemas import (
    LoyaltyWalletResponse,
    RewardCreateRequest,
    RewardRedemptionResponse,
    RewardResponse,
    RewardUpdateRequest,
)
from src.backend.modules.loyalty.service import LoyaltyService

router = APIRouter()

# ── Endpoints Autenticados (Clientes) ────────────────────

@router.get("/me", response_model=LoyaltyWalletResponse)
async def get_my_wallet(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """(Cliente) Consulta o próprio saldo. Cria a carteira automaticamente se for a 1ª vez."""
    service = LoyaltyService(db)
    return await service.get_or_create_wallet(user.id)


@router.get("/rewards", response_model=list[RewardResponse])
async def list_active_rewards(db: AsyncSession = Depends(get_db)):
    """(Cliente) Vê o catálogo de prêmios que podem ser resgatados."""
    service = LoyaltyService(db)
    return await service.list_active_rewards()


@router.post("/redeem/{reward_id}", response_model=RewardRedemptionResponse, status_code=status.HTTP_201_CREATED)
async def redeem_reward(
    reward_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """(Cliente) Tenta resgatar um prêmio debitando do próprio saldo."""
    service = LoyaltyService(db)
    try:
        return await service.redeem_reward(user.id, reward_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Endpoints Administrativos ────────────────────────────

@router.post("/rewards", response_model=RewardResponse, status_code=status.HTTP_201_CREATED)
async def create_reward(
    data: RewardCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Cria um novo prêmio no catálogo."""
    service = LoyaltyService(db)
    return await service.create_reward(data)


@router.put("/rewards/{reward_id}", response_model=RewardResponse)
async def update_reward(
    reward_id: uuid.UUID,
    data: RewardUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Edita dados de um prêmio existente."""
    service = LoyaltyService(db)
    reward = await service.update_reward(reward_id, data)
    if not reward:
        raise HTTPException(status_code=404, detail="Prêmio não encontrado.")
    return reward


@router.post("/wallet/{target_user_id}/add", response_model=LoyaltyWalletResponse)
async def add_points_manually(
    target_user_id: uuid.UUID,
    points: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Concede pontos manualmente a um cliente."""
    service = LoyaltyService(db)
    try:
        return await service.add_points(target_user_id, points)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/redemptions", response_model=list[RewardRedemptionResponse])
async def list_redemptions(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Visualiza o histórico geral de resgates feitos."""
    service = LoyaltyService(db)
    return await service.list_redemptions()
