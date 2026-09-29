"""
Trim — Expenses Schemas

Schemas Pydantic para as categorias e registros de despesas.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ── Categorias ───────────────────────────────────────────

class ExpenseCategoryCreateRequest(BaseModel):
    name: str = Field(..., max_length=100)


class ExpenseCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    created_at: datetime


# ── Despesas ─────────────────────────────────────────────

class ExpenseCreateRequest(BaseModel):
    category_id: uuid.UUID | None = None
    description: str = Field(..., max_length=255)
    amount: Decimal = Field(..., gt=0)
    payment_date: date
    is_recurring: bool = False


class ExpenseUpdateRequest(BaseModel):
    category_id: uuid.UUID | None = None
    description: str | None = Field(None, max_length=255)
    amount: Decimal | None = Field(None, gt=0)
    payment_date: date | None = None
    is_recurring: bool | None = None


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
