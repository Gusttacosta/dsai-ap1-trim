"""
Trim — Services Schemas

Schemas Pydantic para validação do módulo de serviços.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.backend.modules.barbers.schemas import BarberPublicResponse


# Limites das colunas e da agenda (SPEC/2026-11-22-servicos-validacao-reativacao.md).
# Acima deles, o PostgreSQL recusava o valor e a rota respondia 500.
MAX_PRICE = Decimal("99999999.99")  # Numeric(10, 2)
MAX_DURATION_MINUTES = 12 * 60  # um dia inteiro de trabalho
NAME_MIN, NAME_MAX = 2, 100


class ServiceCreateRequest(BaseModel):
    """Payload para criação de um novo serviço."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=NAME_MIN, max_length=NAME_MAX)
    description: str | None = None
    price: Decimal = Field(..., ge=0, le=MAX_PRICE)
    duration_minutes: int = Field(..., gt=0, le=MAX_DURATION_MINUTES)


class ServiceUpdateRequest(BaseModel):
    """Alteração parcial. `null` só é aceito na descrição, que pode ser apagada."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, min_length=NAME_MIN, max_length=NAME_MAX)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0, le=MAX_PRICE)
    duration_minutes: int | None = Field(None, gt=0, le=MAX_DURATION_MINUTES)
    is_active: bool | None = None

    @field_validator("name", "price", "duration_minutes", "is_active")
    @classmethod
    def reject_null(cls, v):
        # Só roda para campos enviados: o null explícito gravaria None numa coluna NOT NULL.
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo")
        return v


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
