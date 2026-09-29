"""
Trim — Subscriptions Schemas

Schemas Pydantic para validação do módulo de assinaturas.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.backend.modules.subscriptions.models import SubscriptionStatus


# ── Planos ───────────────────────────────────────────────

class SubscriptionPlanCreateRequest(BaseModel):
    """Payload para criar um plano de assinatura."""
    name: str = Field(..., max_length=100)
    description: str | None = None
    monthly_price: Decimal = Field(..., gt=0)
    included_cuts: int = Field(default=0, ge=0)
    included_shaves: int = Field(default=0, ge=0)
    discount_percentage: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)


class SubscriptionPlanUpdateRequest(BaseModel):
    """Payload para editar um plano de assinatura."""
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    monthly_price: Decimal | None = Field(None, gt=0)
    included_cuts: int | None = Field(None, ge=0)
    included_shaves: int | None = Field(None, ge=0)
    discount_percentage: Decimal | None = Field(None, ge=0, le=100)


class SubscriptionPlanResponse(BaseModel):
    """Resposta com dados de um plano."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    monthly_price: Decimal
    included_cuts: int
    included_shaves: int
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
