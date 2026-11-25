"""
Trim — Loyalty Schemas

Schemas Pydantic para validação do programa de fidelidade.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoyaltyWalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    balance: int
    lifetime_points: int
    updated_at: datetime


class LoyaltyWalletAdminResponse(LoyaltyWalletResponse):
    """Carteira com o cliente, para a lista do admin (#73)."""
    full_name: str
    email: str


class RewardCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    points_cost: int = Field(..., gt=0)


class RewardUpdateRequest(BaseModel):
    """Alteração parcial. `null` só é aceito na descrição, que pode ser apagada."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    points_cost: int | None = Field(None, gt=0)
    is_active: bool | None = None

    @field_validator("name", "points_cost", "is_active")
    @classmethod
    def reject_null(cls, v):
        # Só roda para campos enviados: o null explícito gravaria None numa coluna NOT NULL (#73).
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo")
        return v


class RewardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    points_cost: int
    is_active: bool
    created_at: datetime


class RewardRedemptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    wallet_id: uuid.UUID
    user_id: uuid.UUID
    reward_id: uuid.UUID
    points_spent: int
    redeemed_at: datetime

    reward: RewardResponse
