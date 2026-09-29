"""
Trim — Notifications Router

Endpoints de notificações para os usuários.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin, get_current_user
from src.backend.modules.auth.models import User
from src.backend.modules.notifications.schemas import (
    NotificationBroadcastRequest,
    NotificationResponse,
    UnreadCountResponse,
)
from src.backend.modules.notifications.service import NotificationService

router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
async def list_my_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """(Geral) Lista todas as notificações recebidas pelo usuário logado."""
    service = NotificationService(db)
    return await service.get_my_notifications(user.id)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """(Geral) Retorna a quantidade de notificações não lidas."""
    service = NotificationService(db)
    count = await service.count_unread(user.id)
    return UnreadCountResponse(count=count)


@router.put("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """(Geral) Marca todas as notificações do usuário como lidas de uma vez."""
    service = NotificationService(db)
    affected = await service.mark_all_as_read(user.id)
    return {"detail": f"{affected} notificações marcadas como lidas."}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """(Geral) Marca uma notificação específica como lida."""
    service = NotificationService(db)
    notif = await service.mark_as_read(notification_id, user.id)
    
    if not notif:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    return notif


@router.post("/broadcast", status_code=status.HTTP_201_CREATED)
async def broadcast_alert(
    data: NotificationBroadcastRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Dispara um alerta geral para todos os usuários cadastrados."""
    service = NotificationService(db)
    affected = await service.broadcast(data)
    return {"detail": f"Mensagem enviada para {affected} usuários."}
