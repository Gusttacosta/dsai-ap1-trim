"""
Trim — Products Schemas

Schemas Pydantic para validação de produtos e inventário.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.backend.modules.products.models import MovementType


# ── Produtos ─────────────────────────────────────────────

def blank_sku_is_none(value: str | None) -> str | None:
    """SKU vazio é ausência de SKU: dois "" estouravam a coluna única com 500 (#61)."""
    return value or None


class ProductCreateRequest(BaseModel):
    """Payload para criar um novo produto."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = None
    sku: str | None = Field(None, max_length=50)
    price: Decimal = Field(..., ge=0)
    cost_price: Decimal | None = Field(None, ge=0)
    # A coluna é String(500): acima disso a rota respondia 500 (#61).
    image_url: str | None = Field(None, max_length=500)

    _sku = field_validator("sku")(blank_sku_is_none)


class ProductUpdateRequest(BaseModel):
    """Payload para atualizar dados base do produto (exceto estoque).

    `null` só é aceito nos campos opcionais (descrição, SKU, custo e foto). `is_active` reativa
    ou desativa o produto (#61)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = None
    sku: str | None = Field(None, max_length=50)
    price: Decimal | None = Field(None, ge=0)
    cost_price: Decimal | None = Field(None, ge=0)
    image_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None

    _sku = field_validator("sku")(blank_sku_is_none)

    @field_validator("name", "price", "is_active")
    @classmethod
    def reject_null(cls, v):
        # Só roda para campos enviados: o null explícito gravaria None numa coluna NOT NULL (#61).
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo")
        return v


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
    """Payload para registrar uma entrada ou saída de estoque.

    O sinal acompanha o tipo (#61): `restock` é entrada (positiva), `sale` e `loss` são saídas
    (negativas), e `adjustment` pode ir para os dois lados. Zero não é movimentação."""
    quantity: int = Field(..., description="Quantidade (negativa para saída, positiva para entrada)")
    movement_type: MovementType
    notes: str | None = None

    @model_validator(mode="after")
    def sign_matches_type(self):
        if self.quantity == 0:
            raise ValueError("A quantidade não pode ser zero.")
        if self.movement_type == MovementType.RESTOCK and self.quantity < 0:
            raise ValueError("Reposição (restock) é uma entrada: a quantidade deve ser positiva.")
        if self.movement_type in (MovementType.SALE, MovementType.LOSS) and self.quantity > 0:
            raise ValueError("Venda e perda são saídas: a quantidade deve ser negativa.")
        return self


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
