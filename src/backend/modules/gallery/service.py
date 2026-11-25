"""
Trim — Gallery Service

Regras de negócio de moderação e listagem de fotos.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.modules.gallery.models import GalleryTag, PortfolioImage
from src.backend.modules.auth.models import User
from src.backend.modules.barbers.models import Barber
from src.backend.modules.gallery.schemas import (
    GalleryTagCreateRequest,
    GalleryTagUpdateRequest,
    PortfolioImageCreateRequest,
)
from src.backend.modules.notifications.models import Notification, NotificationType
from src.backend.modules.services.models import Service


class GalleryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Tags ─────────────────────────────────────────────────

    async def create_tag(self, data: GalleryTagCreateRequest) -> GalleryTag:
        stmt = select(GalleryTag).where(GalleryTag.name == data.name)
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ValueError(f"A tag '{data.name}' já existe.")

        tag = GalleryTag(name=data.name)
        self.db.add(tag)
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def rename_tag(self, tag_id: uuid.UUID, data: GalleryTagUpdateRequest) -> GalleryTag | None:
        tag = await self.db.get(GalleryTag, tag_id)
        if tag is None:
            return None
        stmt = select(GalleryTag.id).where(GalleryTag.name == data.name, GalleryTag.id != tag_id)
        if (await self.db.execute(stmt)).first():
            raise ValueError(f"A tag '{data.name}' já existe.")
        tag.name = data.name
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def delete_tag(self, tag_id: uuid.UUID) -> bool:
        """Apaga a tag. As fotos continuam, sem ela (a tabela de ligação tem ON DELETE CASCADE)."""
        result = await self.db.execute(delete(GalleryTag).where(GalleryTag.id == tag_id))
        await self.db.commit()
        return result.rowcount > 0

    async def list_tags(self) -> list[GalleryTag]:
        stmt = select(GalleryTag).order_by(GalleryTag.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    # ── Fotos (Portfolio) ────────────────────────────────────

    async def upload_image(self, barber_id: uuid.UUID, data: PortfolioImageCreateRequest, auto_approve: bool = False) -> PortfolioImage:
        """Adiciona a referência da foto. Se for admin, auto_approve=True."""
        # Sem esta checagem, a FK estoura no commit e a rota responde 500 (#71).
        if data.service_id is not None and await self.db.get(Service, data.service_id) is None:
            raise LookupError("Serviço não encontrado.")

        # Busca as tags solicitadas. Antes, uma tag desconhecida era ignorada sem aviso (#71).
        tags = []
        if data.tag_ids:
            stmt_tags = select(GalleryTag).where(GalleryTag.id.in_(data.tag_ids))
            result = await self.db.execute(stmt_tags)
            tags = list(result.scalars().all())
            if len(tags) != len(set(data.tag_ids)):
                raise LookupError("Uma ou mais tags não existem.")

        image = PortfolioImage(
            image_url=str(data.image_url),
            barber_id=barber_id,
            service_id=data.service_id,
            description=data.description,
            is_approved=auto_approve,
            tags=tags
        )
        
        self.db.add(image)
        await self.db.commit()
        
        stmt_refresh = select(PortfolioImage).where(PortfolioImage.id == image.id).options(selectinload(PortfolioImage.tags))
        result = await self.db.execute(stmt_refresh)
        return result.scalar_one()

    async def list_approved_images(self, barber_id: uuid.UUID | None = None, tag_id: uuid.UUID | None = None) -> list[PortfolioImage]:
        """Lista fotos públicas (is_approved=True) com filtros opcionais."""
        # Fotos de barbeiro desativado (perfil ou conta) saem da galeria pública (#71).
        stmt = (
            select(PortfolioImage)
            .join(Barber, PortfolioImage.barber_id == Barber.id)
            .join(User, Barber.user_id == User.id)
            .where(PortfolioImage.is_approved.is_(True), Barber.is_active.is_(True), User.is_active.is_(True))
            .options(selectinload(PortfolioImage.tags))
        )
        
        if barber_id:
            stmt = stmt.where(PortfolioImage.barber_id == barber_id)
            
        if tag_id:
            stmt = stmt.where(PortfolioImage.tags.any(GalleryTag.id == tag_id))
            
        stmt = stmt.order_by(PortfolioImage.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_images(self) -> list[PortfolioImage]:
        """(Admin) Lista fotos aguardando aprovação."""
        stmt = select(PortfolioImage).where(PortfolioImage.is_approved == False).options(selectinload(PortfolioImage.tags))
        stmt = stmt.order_by(PortfolioImage.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def approve_image(self, image_id: uuid.UUID) -> PortfolioImage:
        """(Admin) Aprova uma foto para exibição pública."""
        stmt = select(PortfolioImage).where(PortfolioImage.id == image_id).options(selectinload(PortfolioImage.tags))
        image = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not image:
            raise ValueError("Imagem não encontrada.")
            
        image.is_approved = True
        await self.db.commit()
        return image

    async def unapprove_image(self, image_id: uuid.UUID) -> PortfolioImage | None:
        """(Admin) Tira a foto da galeria pública; ela volta para a fila de moderação (#71)."""
        image = await self.db.get(PortfolioImage, image_id)
        if image is None:
            return None
        image.is_approved = False
        await self.db.commit()
        result = await self.db.execute(
            select(PortfolioImage).where(PortfolioImage.id == image_id).options(selectinload(PortfolioImage.tags))
        )
        return result.scalar_one()

    async def reject_image(self, image_id: uuid.UUID, reason: str) -> bool:
        """(Admin) Recusa uma foto pendente: apaga a foto e avisa o barbeiro com o motivo (#71)."""
        image = await self.db.get(PortfolioImage, image_id)
        if image is None:
            return False
        if image.is_approved:
            raise ValueError("A foto já foi aprovada. Para tirá-la da galeria, use a remoção da aprovação.")
        user_id = (await self.db.execute(select(Barber.user_id).where(Barber.id == image.barber_id))).scalar_one()
        self.db.add(Notification(
            user_id=user_id,
            title="Foto recusada na galeria",
            message=f"A foto {image.image_url} foi recusada. Motivo: {reason}",
            type=NotificationType.SYSTEM_ALERT,
        ))
        await self.db.delete(image)
        await self.db.commit()
        return True

    async def delete_image(
        self, image_id: uuid.UUID, requesting_barber_id: uuid.UUID | None = None, *, is_admin: bool = False
    ) -> bool:
        """Deleta a imagem. Fora do admin, só o dono apaga: sem barbeiro, não há posse (#71)."""
        stmt = select(PortfolioImage).where(PortfolioImage.id == image_id)
        image = (await self.db.execute(stmt)).scalar_one_or_none()

        if not image:
            return False

        if not is_admin and image.barber_id != requesting_barber_id:
            raise ValueError("Você não tem permissão para deletar a foto de outro barbeiro.")
            
        await self.db.delete(image)
        await self.db.commit()
        return True
