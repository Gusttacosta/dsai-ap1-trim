"""
Trim — Notifications Schemas

Schemas Pydantic para validação e resposta de notificações.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.backend.modules.notifications.models import NotificationType


class NotificationCreateRequest(BaseModel):
    """Payload interno (ou de admin) para gerar uma notificação para um usuário específico."""
    user_id: uuid.UUID
    title: str = Field(..., max_length=150)
    message: str
    type: NotificationType


class NotificationBroadcastRequest(BaseModel):
    """Payload de Admin para enviar a mesma mensagem a um público (#75)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    # Título e mensagem vazios eram aceitos (#75).
    title: str = Field(..., min_length=1, max_length=150)
    message: str = Field(..., min_length=1, max_length=2000)
    audience: Literal["all", "clients", "barbers", "admins"] = "all"


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: datetime


class UnreadCountResponse(BaseModel):
    count: int
