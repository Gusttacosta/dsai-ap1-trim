"""
Trim — Products Schemas

Schemas Pydantic para validação de produtos e inventário.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.backend.modules.products.models import MovementType


# ── Produtos ─────────────────────────────────────────────

class ProductCreateRequest(BaseModel):
    """Payload para criar um novo produto."""
    name: str = Field(..., max_length=150)
    description: str | None = None
    sku: str | None = Field(None, max_length=50)
    price: Decimal = Field(..., ge=0)
    cost_price: Decimal | None = Field(None, ge=0)
    image_url: str | None = None


class ProductUpdateRequest(BaseModel):
    """Payload para atualizar dados base do produto (exceto estoque)."""
    name: str | None = Field(None, max_length=150)
    description: str | None = None
    sku: str | None = Field(None, max_length=50)
    price: Decimal | None = Field(None, ge=0)
    cost_price: Decimal | None = Field(None, ge=0)
    image_url: str | None = None


class ProductPublicResponse(BaseModel):
    """Resposta pública da vitrine (omite cost_price)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    sku: str | None
    price: Decimal
    stock_quantity: int
    is_active: bool
    image_url: str | None


class ProductAdminResponse(ProductPublicResponse):
    """Resposta administrativa (inclui cost_price e campos sensíveis)."""
    cost_price: Decimal | None
    created_at: datetime
    updated_at: datetime


# ── Inventário ───────────────────────────────────────────

class InventoryMovementRequest(BaseModel):
    """Payload para registrar uma entrada ou saída de estoque."""
    quantity: int = Field(..., description="Quantidade (negativa para saída, positiva para entrada)")
    movement_type: MovementType
    notes: str | None = None


class InventoryMovementResponse(BaseModel):
    """Histórico de uma movimentação."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    user_id: uuid.UUID
    quantity: int
    movement_type: MovementType
    notes: str | None
    created_at: datetime
