"""
Trim — Subscriptions Service

Regras de negócio de gerenciamento de planos e ciclo de vida de assinaturas.
"""

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.modules.subscriptions.models import SubscriptionPlan, SubscriptionStatus, UserSubscription
from src.backend.modules.subscriptions.schemas import SubscriptionPlanCreateRequest, SubscriptionPlanUpdateRequest


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Planos (Admin) ───────────────────────────────────────

    async def create_plan(self, data: SubscriptionPlanCreateRequest) -> SubscriptionPlan:
        """Cria um novo plano de assinatura."""
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.name == data.name)
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ValueError("Já existe um plano com esse nome.")

        plan = SubscriptionPlan(**data.model_dump())
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def update_plan(self, plan_id: uuid.UUID, data: SubscriptionPlanUpdateRequest) -> SubscriptionPlan | None:
        """Edita dados de um plano existente."""
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        plan = (await self.db.execute(stmt)).scalar_one_or_none()
        if not plan:
            return None

        if data.name is not None and data.name != plan.name:
            stmt_name = select(SubscriptionPlan).where(SubscriptionPlan.name == data.name)
            if (await self.db.execute(stmt_name)).scalar_one_or_none():
                raise ValueError("Já existe um plano com esse nome.")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(plan, key, value)

        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def deactivate_plan(self, plan_id: uuid.UUID) -> bool:
        """Faz soft delete de um plano (não afeta assinaturas vigentes)."""
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        plan = (await self.db.execute(stmt)).scalar_one_or_none()
        if not plan:
            return False

        plan.is_active = False
        await self.db.commit()
        return True

    async def list_active_plans(self) -> list[SubscriptionPlan]:
        """Lista planos disponíveis para compra."""
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True).order_by(SubscriptionPlan.monthly_price)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    # ── Assinaturas (Clientes) ───────────────────────────────

    async def get_user_subscription(self, user_id: uuid.UUID) -> UserSubscription | None:
        """Retorna a assinatura atual do usuário (se tiver)."""
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .options(selectinload(UserSubscription.plan))
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def subscribe(self, user_id: uuid.UUID, plan_id: uuid.UUID) -> UserSubscription:
        """Cliente assina um plano. Calcula +30 dias de expiração."""
        # 1. Verifica se o plano existe e está ativo
        stmt_plan = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        plan = (await self.db.execute(stmt_plan)).scalar_one_or_none()
        if not plan or not plan.is_active:
            raise ValueError("Plano inválido ou indisponível.")

        # 2. Verifica se o usuário já tem uma assinatura
        existing = await self.get_user_subscription(user_id)
        if existing:
            # Se já tem, pode ser que esteja CANCELED mas ainda no grace period (end_date no futuro).
            # Por simplicidade da Spec, rejeitamos assinar se o registro existe.
            # O cliente deveria esperar expirar ou implementar lógica de Upgrade/Downgrade complexa.
            raise ValueError("O usuário já possui uma assinatura ativa ou em período de carência. Cancele-a ou aguarde expirar.")

        # 3. Cria a assinatura com ciclo de 30 dias
        start_date = date.today()
        end_date = start_date + timedelta(days=30)

        subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            start_date=start_date,
            end_date=end_date,
            status=SubscriptionStatus.ACTIVE
        )
        self.db.add(subscription)
        await self.db.commit()

        # Recarrega para popular o `.plan`
        return await self.get_user_subscription(user_id)

    async def cancel_subscription(self, user_id: uuid.UUID) -> UserSubscription | None:
        """Cancela a renovação. Mantém usável até end_date."""
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return None

        if subscription.status == SubscriptionStatus.CANCELED:
            raise ValueError("Esta assinatura já está cancelada.")

        subscription.status = SubscriptionStatus.CANCELED
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription
