"""
Trim — Subscriptions Service

Regras de negócio de gerenciamento de planos e ciclo de vida de assinaturas.
"""

import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, null, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.config import settings
from src.backend.modules.auth.models import User
from src.backend.modules.finance.models import PaymentMethod, Transaction, TransactionType
from src.backend.modules.notifications.models import Notification, NotificationType
from src.backend.modules.subscriptions.models import SubscriptionPlan, SubscriptionStatus, UserSubscription
from src.backend.modules.subscriptions.schemas import SubscriptionPlanCreateRequest, SubscriptionPlanUpdateRequest


CYCLE_DAYS = 30
UNLIMITED_FIELDS = ("included_cuts", "included_shaves")
ALREADY_ERROR = (
    "O usuário já possui uma assinatura ativa ou em período de carência. Cancele-a ou aguarde expirar."
)


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _today(self) -> date:
        # Dia da barbearia, e não o do servidor em UTC (#64).
        return datetime.now(ZoneInfo(settings.shop_timezone)).date()

    async def _notify(self, user_id: uuid.UUID, title: str, message: str) -> None:
        """Aviso do Trim Club ao sócio, no mesmo commit (#64 e #75). Conta desativada não recebe."""
        user = await self.db.get(User, user_id)
        if user is not None and user.is_active:
            self.db.add(Notification(
                user_id=user_id, title=title, message=message, type=NotificationType.SUBSCRIPTION_NOTICE
            ))

    # ── Planos (Admin) ───────────────────────────────────────

    async def create_plan(self, data: SubscriptionPlanCreateRequest) -> SubscriptionPlan:
        """Cria um novo plano de assinatura."""
        # Nome único sem diferenciar maiúsculas (#64).
        stmt = select(SubscriptionPlan).where(func.lower(SubscriptionPlan.name) == data.name.lower())
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ValueError("Já existe um plano com esse nome.")

        # None explícito vira NULL (ilimitado, #16); sem null(), o ORM aplicaria o default 0 da coluna.
        values = {k: (null() if v is None and k in UNLIMITED_FIELDS else v) for k, v in data.model_dump().items()}
        plan = SubscriptionPlan(**values)
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
            stmt_name = select(SubscriptionPlan).where(
                func.lower(SubscriptionPlan.name) == data.name.lower(), SubscriptionPlan.id != plan.id
            )
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
        subscription = (await self.db.execute(stmt)).scalar_one_or_none()
        if subscription is not None and self._expire_if_due([subscription]):
            await self.db.commit()
            subscription = (await self.db.execute(stmt.execution_options(populate_existing=True))).scalar_one()
        return subscription

    def _expire_if_due(self, subscriptions: list[UserSubscription]) -> bool:
        """Assinatura ativa depois do end_date vira past_due (#64). Devolve se mudou alguma."""
        today = self._today()
        changed = False
        for sub in subscriptions:
            if sub.status == SubscriptionStatus.ACTIVE and sub.end_date < today:
                sub.status = SubscriptionStatus.PAST_DUE
                changed = True
        return changed

    async def list_all(self) -> list[UserSubscription]:
        """(Admin) Todas as assinaturas, das mais novas para as mais antigas, com o vencimento aplicado."""
        stmt = select(UserSubscription).options(selectinload(UserSubscription.plan)).order_by(
            UserSubscription.created_at.desc()
        )
        subscriptions = list((await self.db.execute(stmt)).scalars().all())
        if self._expire_if_due(subscriptions):
            await self.db.commit()
            subscriptions = list(
                (await self.db.execute(stmt.execution_options(populate_existing=True))).scalars().all()
            )
        return subscriptions

    async def subscribe(
        self, user_id: uuid.UUID, plan_id: uuid.UUID, payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    ) -> UserSubscription:
        """Cliente assina um plano por 30 dias e paga a primeira mensalidade (#64).

        Quem já foi sócio e cuja assinatura terminou (past_due, ou cancelada depois do end_date)
        assina de novo no mesmo registro, porque o user_id é único na tabela."""
        # 1. Verifica se o plano existe e está ativo
        stmt_plan = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        plan = (await self.db.execute(stmt_plan)).scalar_one_or_none()
        if not plan or not plan.is_active:
            raise ValueError("Plano inválido ou indisponível.")

        # 2. Verifica se o usuário já tem uma assinatura
        existing = await self.get_user_subscription(user_id)
        start_date = self._today()
        if existing and existing.status != SubscriptionStatus.PAST_DUE and existing.end_date >= start_date:
            # Ativa, ou cancelada ainda dentro do período pago (carência).
            raise ValueError(ALREADY_ERROR)

        # 3. Ciclo de 30 dias, no registro antigo (renovação) ou num novo
        end_date = start_date + timedelta(days=CYCLE_DAYS)
        if existing:
            subscription = existing
            subscription.plan_id = plan.id
            subscription.start_date = start_date
            subscription.end_date = end_date
            subscription.status = SubscriptionStatus.ACTIVE
        else:
            subscription = UserSubscription(
                user_id=user_id,
                plan_id=plan.id,
                start_date=start_date,
                end_date=end_date,
                status=SubscriptionStatus.ACTIVE
            )
            self.db.add(subscription)
        await self.db.flush()

        # 4. A mensalidade entra no caixa (SPEC/2026-09-29-financeiro.md, #64)
        self.db.add(Transaction(
            type=TransactionType.SUBSCRIPTION,
            reference_id=subscription.id,
            amount=plan.monthly_price,
            payment_method=payment_method,
            user_id=user_id,
        ))
        await self._notify(
            user_id, "Bem-vindo ao Trim Club",
            f"Sua assinatura do plano {plan.name} vale até {end_date.strftime('%d/%m/%Y')}.",
        )
        await self.db.commit()
        self.db.expire(subscription)

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
        await self._notify(
            user_id, "Assinatura cancelada",
            f"Seus benefícios do Trim Club continuam até {subscription.end_date.strftime('%d/%m/%Y')}.",
        )
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription
