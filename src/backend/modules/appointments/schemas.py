"""
Trim — Appointments Schemas

Schemas Pydantic para validação de agendamentos.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.backend.modules.appointments.models import AppointmentStatus
from src.backend.modules.auth.schemas import FULL_NAME_MAX

# Nome do visitante (SPEC/2026-11-23-nome-do-visitante.md). Letra é o que o Unicode chama de
# letra (str.isalpha), a mesma classe do \p{L} usado no frontend (utils/guestName.ts).
GUEST_NAME_PUNCTUATION = "'’.-"


def is_guest_word(word: str) -> bool:
    """Só letras, apóstrofo, hífen e ponto, com pelo menos uma letra."""
    return any(c.isalpha() for c in word) and all(c.isalpha() or c in GUEST_NAME_PUNCTUATION for c in word)


def clean_guest_name(v: str) -> str:
    """Nome e sobrenome do visitante, com os espaços das pontas e repetidos removidos."""
    words = v.split()
    if len(words) < 2 or any(len(word) < 2 for word in words):
        raise ValueError("Informe nome e sobrenome")
    if not all(is_guest_word(word) for word in words):
        raise ValueError("Nome deve ter só letras, espaços, apóstrofo, hífen e ponto")
    name = " ".join(words)
    if len(name) > FULL_NAME_MAX:
        raise ValueError(f"Nome deve ter no máximo {FULL_NAME_MAX} caracteres")
    return name


class AppointmentCreateRequest(BaseModel):
    """Payload para criar um novo agendamento."""
    barber_id: uuid.UUID
    start_datetime: datetime
    service_ids: list[uuid.UUID] = Field(..., min_length=1)
    notes: str | None = None

class GuestAppointmentCreateRequest(AppointmentCreateRequest):
    """Payload para criar um novo agendamento como visitante."""
    guest_name: str

    @field_validator("guest_name")
    @classmethod
    def validate_guest_name(cls, v: str) -> str:
        return clean_guest_name(v)


class AppointmentStatusUpdateRequest(BaseModel):
    """Payload para o barbeiro/admin alterar o status."""
    status: AppointmentStatus


class AppointmentItemResponse(BaseModel):
    """Resposta com dados de um item de serviço congelado."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    service_id: uuid.UUID | None
    service_name: str
    locked_price: Decimal
    duration_minutes: int


class AppointmentResponse(BaseModel):
    """Resposta com os dados completos de um agendamento."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    client_id: uuid.UUID
    barber_id: uuid.UUID
    start_datetime: datetime
    end_datetime: datetime
    status: AppointmentStatus
    total_price: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime
    
    items: list[AppointmentItemResponse]


class AvailabilityResponse(BaseModel):
    """Resposta com slots de horários livres."""
    date: str  # YYYY-MM-DD
    barber_id: uuid.UUID
    available_slots: list[str]  # ["09:00", "09:30", "10:00"]
