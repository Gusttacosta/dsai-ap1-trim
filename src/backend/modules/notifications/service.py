"""
Trim — Notifications Service

Serviço de disparo, leitura e broadcast de notificações.
"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.modules.auth.models import User
from src.backend.modules.notifications.models import Notification, NotificationType
from src.backend.modules.notifications.schemas import NotificationBroadcastRequest, NotificationCreateRequest


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(self, data: NotificationCreateRequest) -> Notification:
        """Cria e envia uma notificação para um usuário específico."""
        notif = Notification(**data.model_dump())
        self.db.add(notif)
        await self.db.commit()
        await self.db.refresh(notif)
        return notif

    async def get_my_notifications(self, user_id: uuid.UUID) -> list[Notification]:
        """Busca histórico de notificações de um usuário."""
        stmt = select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_unread(self, user_id: uuid.UUID) -> int:
        """Conta quantas não foram lidas para a bolinha/badge vermelha no frontend."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        """Marca uma notificação como lida."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )
        notif = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not notif:
            return None
            
        notif.is_read = True
        await self.db.commit()
        await self.db.refresh(notif)
        return notif

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Marca todas as não lidas de um usuário como lidas e retorna a qtde afetada."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def broadcast(self, data: NotificationBroadcastRequest) -> int:
        """(Admin) Envia um alerta geral pra todo mundo cadastrado."""
        # 1. Pega os IDs de todo mundo
        stmt = select(User.id)
        user_ids = (await self.db.execute(stmt)).scalars().all()
        
        # 2. Cria em lote (Bulk Insert)
        # SQLAlchemy permite criar a lista de objs e dar add_all
        notifications = [
            Notification(
                user_id=u_id,
                title=data.title,
                message=data.message,
                type=NotificationType.SYSTEM_ALERT
            )
            for u_id in user_ids
        ]
        
        self.db.add_all(notifications)
        await self.db.commit()
        
        return len(notifications)
