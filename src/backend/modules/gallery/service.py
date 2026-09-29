"""
Trim — Gallery Service

Regras de negócio de moderação e listagem de fotos.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.modules.gallery.models import GalleryTag, PortfolioImage
from src.backend.modules.gallery.schemas import GalleryTagCreateRequest, PortfolioImageCreateRequest


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

    async def list_tags(self) -> list[GalleryTag]:
        stmt = select(GalleryTag).order_by(GalleryTag.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    # ── Fotos (Portfolio) ────────────────────────────────────

    async def upload_image(self, barber_id: uuid.UUID, data: PortfolioImageCreateRequest, auto_approve: bool = False) -> PortfolioImage:
        """Adiciona a referência da foto. Se for admin, auto_approve=True."""
        
        # Busca as tags solicitadas
        tags = []
        if data.tag_ids:
            stmt_tags = select(GalleryTag).where(GalleryTag.id.in_(data.tag_ids))
            result = await self.db.execute(stmt_tags)
            tags = list(result.scalars().all())

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
        stmt = select(PortfolioImage).where(PortfolioImage.is_approved == True).options(selectinload(PortfolioImage.tags))
        
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

    async def delete_image(self, image_id: uuid.UUID, requesting_barber_id: uuid.UUID | None = None) -> bool:
        """Deleta a imagem. Se requesting_barber_id for passado, checa posse."""
        stmt = select(PortfolioImage).where(PortfolioImage.id == image_id)
        image = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not image:
            return False
            
        if requesting_barber_id and image.barber_id != requesting_barber_id:
            raise ValueError("Você não tem permissão para deletar a foto de outro barbeiro.")
            
        await self.db.delete(image)
        await self.db.commit()
        return True
