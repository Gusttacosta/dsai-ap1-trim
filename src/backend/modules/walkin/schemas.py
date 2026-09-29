"""
Trim — Walk-in Schemas

Schemas Pydantic para interagir com a fila de espera.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.backend.modules.walkin.models import WalkInStatus


class WalkInCreateRequest(BaseModel):
    """Payload para adicionar alguém na fila."""
    customer_name: str = Field(..., max_length=150)
    user_id: uuid.UUID | None = None
    requested_service_id: uuid.UUID
    requested_barber_id: uuid.UUID | None = None


class WalkInAssignRequest(BaseModel):
    """Payload de quando o barbeiro puxa o cliente da fila."""
    barber_id: uuid.UUID


class WalkInResponse(BaseModel):
    """Visão completa da entrada na fila (para recepção)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    customer_name: str
    user_id: uuid.UUID | None
    requested_service_id: uuid.UUID
    requested_barber_id: uuid.UUID | None
    status: WalkInStatus
    position: int
    joined_at: datetime
    finished_at: datetime | None


class WalkInLiveResponse(BaseModel):
    """Visão pública/display para a TV."""
    model_config = ConfigDict(from_attributes=True)

    customer_name_masked: str
    position: int
    joined_at: datetime
