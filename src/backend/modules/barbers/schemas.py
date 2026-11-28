"""
Trim — Barbers Schemas

Schemas Pydantic para o módulo de barbeiros.
"""

import uuid
from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


# ── Schemas de Work Schedule ─────────────────────────────
# SPEC/2026-11-23-barbeiros-admin-escala.md: as mesmas regras para um dia e para a semana.

END_BEFORE_START = "O horário de término deve ser após o início."
INCOMPLETE_BREAK = "Informe o início e o fim do almoço, ou nenhum dos dois."
BREAK_INVERTED = "O fim do almoço deve ser após o início do almoço."
BREAK_OUTSIDE = "O almoço deve ficar dentro do expediente."
DAY_CHANGED = "Não é possível trocar o dia de um registro da escala."
SEVEN_DAYS = "Envie os 7 dias da semana (0 a 6), um de cada."


def check_work_day(start: time, end: time, break_start: time | None, break_end: time | None) -> None:
    """Confere um dia de escala completo. Lança ValueError com a mensagem da regra quebrada."""
    if end <= start:
        raise ValueError(END_BEFORE_START)
    if (break_start is None) != (break_end is None):
        raise ValueError(INCOMPLETE_BREAK)
    if break_start is None:
        return
    if break_end <= break_start:
        raise ValueError(BREAK_INVERTED)
    if break_start < start or break_end > end:
        raise ValueError(BREAK_OUTSIDE)


class WorkScheduleFields(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0 = Domingo, 6 = Sábado")
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None
    is_working: bool = True


class WorkScheduleDay(WorkScheduleFields):
    """Um dia completo da escala, como vem na semana inteira."""

    @model_validator(mode="after")
    def validate_day(self):
        check_work_day(self.start_time, self.end_time, self.break_start, self.break_end)
        return self


class WorkScheduleUpdate(BaseModel):
    """Alteração parcial de um dia. As regras são conferidas no service, sobre o resultado."""
    model_config = ConfigDict(extra="forbid")

    day_of_week: int | None = Field(None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    break_start: time | None = None
    break_end: time | None = None
    is_working: bool | None = None

    @field_validator("day_of_week", "start_time", "end_time", "is_working")
    @classmethod
    def reject_null(cls, v):
        # Só roda para campos enviados: null gravaria None numa coluna NOT NULL.
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo")
        return v


class WorkScheduleResponse(WorkScheduleFields):
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
    """Alteração parcial pelo admin. `null` apaga a bio e o Instagram; nos outros, é recusado."""
    model_config = ConfigDict(extra="forbid")

    bio: str | None = Field(None, max_length=500)
    instagram_url: HttpUrl | None = None
    commission_rate: Decimal | None = Field(None, ge=0, le=100)
    is_active: bool | None = None

    @field_validator("commission_rate", "is_active")
    @classmethod
    def reject_null(cls, v):
        if v is None:
            raise ValueError("Campo obrigatório não pode ser nulo")
        return v


class BarberUpdateSelfRequest(BaseModel):
    """O próprio barbeiro altera a bio e o Instagram. `null` apaga o campo."""
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


class BarberSelfResponse(BaseModel):
    """Resposta ao próprio barbeiro: sem a comissão, que só o admin vê (regra 4)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    bio: str | None
    instagram_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BarberAdminResponse(BaseModel):
    """Resposta ao admin: dados do usuário e do perfil, com a comissão e as duas situações."""

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    avatar_url: str | None
    bio: str | None
    instagram_url: str | None
    commission_rate: Decimal
    is_active: bool
    user_is_active: bool
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


class BarberServiceSummary(BaseModel):
    """Serviço habilitado, nos detalhes do barbeiro (item 5 da #39)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    price: Decimal
    duration_minutes: int


class BarberDetailResponse(BarberPublicResponse):
    """Detalhes públicos do barbeiro com os serviços ativos que ele faz."""
    services: list[BarberServiceSummary]
