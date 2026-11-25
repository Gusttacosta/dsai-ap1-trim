"""
Trim — Expenses Schemas

Schemas Pydantic para as categorias e registros de despesas.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# A coluna é Numeric(10, 2): acima disso o PostgreSQL recusa o valor e a rota respondia 500 (#65).
MAX_AMOUNT = Decimal("99999999.99")
CENTS = Decimal("0.01")


def two_places(value: Decimal | None) -> Decimal | None:
    """Devolve o valor como o banco grava (100.5 -> 100.50), para a resposta da criação bater
    com a da listagem (#65)."""
    return None if value is None else value.quantize(CENTS)


# ── Categorias ───────────────────────────────────────────

class ExpenseCategoryCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=100)


class ExpenseCategoryUpdateRequest(ExpenseCategoryCreateRequest):
    """Renomear uma categoria (#65)."""


class ExpenseCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    created_at: datetime


# ── Despesas ─────────────────────────────────────────────

class ExpenseCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category_id: uuid.UUID | None = None
    description: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0, le=MAX_AMOUNT, decimal_places=2)
    payment_date: date
    is_recurring: bool = False

    _two_places = field_validator("amount")(two_places)


class ExpenseUpdateRequest(BaseModel):
    """Alteração parcial. `null` só é aceito na categoria, que pode ser retirada."""
    model_config = ConfigDict(str_strip_whitespace=True)

    category_id: uuid.UUID | None = None
    description: str | None = Field(None, min_length=1, max_length=255)
    amount: Decimal | None = Field(None, gt=0, le=MAX_AMOUNT, decimal_places=2)
    payment_date: date | None = None
    is_recurring: bool | None = None

    @field_validator("description", "amount", "payment_date", "is_recurring")
    @classmethod
    def reject_null(cls, v):
        # Só roda para campos enviados: o null explícito gravaria None numa coluna NOT NULL (#65).
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo")
        return v

    _two_places = field_validator("amount")(two_places)


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID | None
    description: str
    amount: Decimal
    payment_date: date
    is_recurring: bool
    created_at: datetime
    updated_at: datetime

    category: ExpenseCategoryResponse | None
