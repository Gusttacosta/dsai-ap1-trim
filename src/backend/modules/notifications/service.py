"""
Trim — Notifications Service

Serviço de disparo, leitura e broadcast de notificações.
"""

import enum
import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.notifications.models import Notification, NotificationType
from src.backend.modules.notifications.schemas import NotificationBroadcastRequest, NotificationCreateRequest


class Audience(str, enum.Enum):
    """Público do aviso geral (#75)."""
    ALL = "all"
    CLIENTS = "clients"
    BARBERS = "barbers"
    ADMINS = "admins"


AUDIENCE_ROLES = {
    Audience.CLIENTS: [UserRole.CLIENT],
    Audience.BARBERS: [UserRole.BARBER],
    Audience.ADMINS: [UserRole.ADMIN],
}


async def notify(db: AsyncSession, user_id: uuid.UUID, title: str, message: str, kind: NotificationType) -> bool:
    """Prepara uma notificação para o usuário, sem commit: ela entra junto com a operação que a
    gerou. Contas desativadas (inclusive o usuário Visitante) não recebem nada (#75)."""
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return False
    db.add(Notification(user_id=user_id, title=title, message=message, type=kind))
    return True


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

    async def get_my_notifications(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0, unread_only: bool = False
    ) -> list[Notification]:
        """Busca o histórico de notificações de um usuário, paginado (#75)."""
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc(), Notification.id).limit(limit).offset(offset)
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

    async def delete(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Apaga uma notificação do próprio usuário (#75)."""
        stmt = delete(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

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
        """(Admin) Envia um alerta geral para as contas ativas do público escolhido (#75)."""
        # 1. Contas ativas: desativadas e o usuário Visitante não leem notificações
        stmt = select(User.id).where(User.is_active.is_(True))
        if data.audience != Audience.ALL:
            stmt = stmt.where(User.role.in_(AUDIENCE_ROLES[Audience(data.audience)]))
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
