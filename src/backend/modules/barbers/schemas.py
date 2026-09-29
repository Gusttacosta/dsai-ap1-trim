"""
Trim — Barbers Schemas

Schemas Pydantic para o módulo de barbeiros.
"""

import uuid
from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


# ── Schemas de Work Schedule ─────────────────────────────

class WorkScheduleBase(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0 = Domingo, 6 = Sábado")
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None
    is_working: bool = True

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: time, info) -> time:
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("O horário de término deve ser após o início.")
        return v

    @field_validator("break_end")
    @classmethod
    def validate_break(cls, v: time | None, info) -> time | None:
        if v is not None and info.data.get("break_start") is not None:
            if v <= info.data["break_start"]:
                raise ValueError("O fim do intervalo deve ser após o início do intervalo.")
        return v


class WorkScheduleCreate(WorkScheduleBase):
    pass


class WorkScheduleUpdate(WorkScheduleBase):
    pass


class WorkScheduleResponse(WorkScheduleBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    barber_id: uuid.UUID


# ── Schemas de Barber ────────────────────────────────────

class BarberCreateRequest(BaseModel):
    """Payload enviado pelo admin para promover um user a barber."""
    user_id: uuid.UUID
    bio: str | None = Field(None, max_length=500)
    instagram_url: HttpUrl | None = None
    commission_rate: Decimal = Field(default=Decimal("50.0"), ge=0, le=100)


class BarberUpdateAdminRequest(BaseModel):
    """Payload para o admin atualizar qualquer dado do barbeiro."""
    bio: str | None = Field(None, max_length=500)
    instagram_url: HttpUrl | None = None
    commission_rate: Decimal | None = Field(None, ge=0, le=100)
    is_active: bool | None = None


class BarberUpdateSelfRequest(BaseModel):
    """Payload para o próprio barbeiro atualizar seus dados (restrito)."""
    bio: str | None = Field(None, max_length=500)
    instagram_url: HttpUrl | None = None


class BarberResponse(BaseModel):
    """Resposta com dados exclusivos do barbeiro."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    user_id: uuid.UUID
    bio: str | None
    instagram_url: str | None
    commission_rate: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BarberPublicResponse(BaseModel):
    """Resposta pública (vitrine) mesclando dados de User e Barber."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID  # ID do Barber
    user_id: uuid.UUID
    full_name: str
    avatar_url: str | None
    bio: str | None
    instagram_url: str | None
    
    # A comissão não é pública!
