"""
Trim — Loyalty Schemas

Schemas Pydantic para validação do programa de fidelidade.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoyaltyWalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    user_id: uuid.UUID
    balance: int
    lifetime_points: int
    updated_at: datetime


class RewardCreateRequest(BaseModel):
    name: str = Field(..., max_length=150)
    description: str | None = Field(None, max_length=500)
    points_cost: int = Field(..., gt=0)


class RewardUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=150)
    description: str | None = Field(None, max_length=500)
    points_cost: int | None = Field(None, gt=0)
    is_active: bool | None = None


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
    reward_id: uuid.UUID
    points_spent: int
    redeemed_at: datetime

    reward: RewardResponse
