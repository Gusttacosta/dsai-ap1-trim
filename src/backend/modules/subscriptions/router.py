"""
Trim — Subscriptions Router

Endpoints para gerenciar os planos do Trim Club e as assinaturas dos clientes.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin, get_current_user
from src.backend.modules.auth.models import User
from src.backend.modules.subscriptions.models import UserSubscription
from src.backend.modules.subscriptions.schemas import (
    SubscriptionPlanCreateRequest,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdateRequest,
    UserSubscriptionResponse,
)
from src.backend.modules.subscriptions.service import SubscriptionService

router = APIRouter()


# ── Planos (Público / Admin) ─────────────────────────────

@router.get("/plans", response_model=list[SubscriptionPlanResponse], summary="Lista planos ativos")
async def list_plans(db: AsyncSession = Depends(get_db)):
    """(Público) Retorna os planos do Trim Club disponíveis para assinatura."""
    service = SubscriptionService(db)
    return await service.list_active_plans()


@router.post("/plans", response_model=SubscriptionPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: SubscriptionPlanCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Cria um novo plano."""
    service = SubscriptionService(db)
    try:
        return await service.create_plan(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def update_plan(
    plan_id: uuid.UUID,
    data: SubscriptionPlanUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Atualiza nome, preço ou benefícios de um plano."""
    service = SubscriptionService(db)
    try:
        plan = await service.update_plan(plan_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")
    return plan


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Oculta um plano (quem já tem, continua com ele)."""
    service = SubscriptionService(db)
    success = await service.deactivate_plan(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")


# ── Assinaturas (Clientes / Admin) ───────────────────────

@router.get("/me", response_model=UserSubscriptionResponse)
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """(Cliente) Consulta a assinatura atual logada e seus benefícios."""
    service = SubscriptionService(db)
    subscription = await service.get_user_subscription(current_user.id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Você não possui uma assinatura.")
    return subscription


@router.post("/me/subscribe/{plan_id}", response_model=UserSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_to_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """(Cliente) Assina um plano (se não tiver outro ativo)."""
    service = SubscriptionService(db)
    try:
        return await service.subscribe(current_user.id, plan_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/me/cancel", response_model=UserSubscriptionResponse)
async def cancel_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """(Cliente) Cancela a renovação. A assinatura vira CANCELED, mas vale até o end_date."""
    service = SubscriptionService(db)
    try:
        subscription = await service.cancel_subscription(current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not subscription:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada.")
    return subscription


@router.get("/users", response_model=list[UserSubscriptionResponse])
async def list_all_subscriptions(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Lista todas as assinaturas do clube (ativas e inativas)."""
    # Exemplo de query direta no router para poupar tempo, usando selectinload para carregar os planos
    from sqlalchemy.orm import selectinload
    stmt = select(UserSubscription).options(selectinload(UserSubscription.plan)).order_by(UserSubscription.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
