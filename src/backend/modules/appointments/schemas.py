"""
Trim — Appointments Schemas

Schemas Pydantic para validação de agendamentos.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.backend.modules.appointments.models import AppointmentStatus


class AppointmentCreateRequest(BaseModel):
    """Payload para criar um novo agendamento."""
    barber_id: uuid.UUID
    start_datetime: datetime
    service_ids: list[uuid.UUID] = Field(..., min_length=1)
    notes: str | None = None


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
