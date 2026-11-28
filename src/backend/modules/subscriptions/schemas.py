"""
Trim — Subscriptions Schemas

Schemas Pydantic para validação do módulo de assinaturas.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.backend.modules.finance.models import PaymentMethod

from src.backend.modules.subscriptions.models import SubscriptionStatus


# ── Planos ───────────────────────────────────────────────

class SubscriptionPlanCreateRequest(BaseModel):
    """Payload para criar um plano de assinatura."""
    model_config = ConfigDict(str_strip_whitespace=True)

    # Nome vazio era aceito (#64).
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    monthly_price: Decimal = Field(..., gt=0)
    # null = ilimitado (#16); omitido = 0 (não incluso)
    included_cuts: int | None = Field(default=0, ge=0)
    included_shaves: int | None = Field(default=0, ge=0)
    discount_percentage: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)


class SubscriptionPlanUpdateRequest(BaseModel):
    """Payload para editar um plano de assinatura.

    `null` só é aceito na descrição e nas quantidades, em que significa "ilimitado" (#16).
    `is_active` reativa ou desativa o plano (#64)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    monthly_price: Decimal | None = Field(None, gt=0)
    included_cuts: int | None = Field(None, ge=0)
    included_shaves: int | None = Field(None, ge=0)
    discount_percentage: Decimal | None = Field(None, ge=0, le=100)
    is_active: bool | None = None

    @field_validator(
        "name", "monthly_price", "discount_percentage", "is_active"
    )
    @classmethod
    def reject_null(cls, v):
        # Só roda para campos enviados: o null explícito gravaria None numa coluna NOT NULL (#64).
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo")
        return v


class SubscribeRequest(BaseModel):
    """Forma de pagamento da mensalidade (#64). O corpo é opcional: o padrão é cartão de crédito."""
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD

    @field_validator("payment_method")
    @classmethod
    def not_club_credit(cls, v: PaymentMethod) -> PaymentMethod:
        if v == PaymentMethod.TRIM_CLUB_CREDIT:
            raise ValueError("A mensalidade não pode ser paga com crédito do próprio Trim Club.")
        return v


class SubscriptionPlanResponse(BaseModel):
    """Resposta com dados de um plano."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    monthly_price: Decimal
    included_cuts: int | None
    included_shaves: int | None
    discount_percentage: Decimal
    is_active: bool
    created_at: datetime


# ── Assinaturas (User) ───────────────────────────────────

class UserSubscriptionResponse(BaseModel):
    """Resposta com os dados da assinatura do cliente e os detalhes do plano."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    plan_id: uuid.UUID
    start_date: date
    end_date: date
    status: SubscriptionStatus
    created_at: datetime
    updated_at: datetime

    plan: SubscriptionPlanResponse
