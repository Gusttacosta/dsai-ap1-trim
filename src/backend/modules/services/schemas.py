"""
Trim — Services Schemas

Schemas Pydantic para validação do módulo de serviços.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.backend.modules.barbers.schemas import BarberPublicResponse


class ServiceCreateRequest(BaseModel):
    """Payload para criação de um novo serviço."""
    name: str = Field(..., max_length=100)
    description: str | None = None
    price: Decimal = Field(..., ge=0)
    duration_minutes: int = Field(..., gt=0)


class ServiceUpdateRequest(BaseModel):
    """Payload para atualização de serviço existente."""
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    duration_minutes: int | None = Field(None, gt=0)


class ServiceResponse(BaseModel):
    """Resposta com dados de um serviço."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    price: Decimal
    duration_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceWithBarbersResponse(ServiceResponse):
    """Resposta de um serviço incluindo a lista de barbeiros habilitados."""
    barbers: list[BarberPublicResponse]
