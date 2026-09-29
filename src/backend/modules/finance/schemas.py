"""
Trim — Finance Schemas

Schemas Pydantic para validação do módulo financeiro.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.backend.modules.finance.models import PaymentMethod, TransactionType


class AppointmentCheckoutRequest(BaseModel):
    """Payload para fechar a conta de um agendamento."""
    payment_method: PaymentMethod


class ProductCheckoutRequest(BaseModel):
    """Payload para venda avulsa de um produto no balcão."""
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    payment_method: PaymentMethod
    user_id: uuid.UUID | None = None  # Opcional, caso não queira identificar o cliente


class TransactionResponse(BaseModel):
    """Resposta com dados de uma transação."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: TransactionType
    reference_id: uuid.UUID
    amount: Decimal
    payment_method: PaymentMethod
    user_id: uuid.UUID | None
    created_at: datetime


class CommissionResponse(BaseModel):
    """Resposta com dados de comissão do barbeiro."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    barber_id: uuid.UUID
    transaction_id: uuid.UUID
    amount: Decimal
    is_paid: bool
    created_at: datetime
    paid_at: datetime | None


class PayCommissionsRequest(BaseModel):
    """Payload para acerto de contas com o barbeiro."""
    barber_id: uuid.UUID
    commission_ids: list[uuid.UUID] = Field(..., min_length=1)
