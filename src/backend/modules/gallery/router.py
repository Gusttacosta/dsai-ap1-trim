"""
Trim — Gallery Router

Endpoints para galeria pública e gestão de fotos por barbeiros e admins.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin, get_current_barber_or_admin
from src.backend.modules.auth.models import Role, User
from src.backend.modules.barbers.models import Barber
from src.backend.modules.gallery.schemas import (
    GalleryTagCreateRequest,
    GalleryTagResponse,
    PortfolioImageCreateRequest,
    PortfolioImageResponse,
)
from src.backend.modules.gallery.service import GalleryService

router = APIRouter()

# ── Endpoints Públicos ───────────────────────────────────

@router.get("", response_model=list[PortfolioImageResponse])
async def list_gallery(
    barber_id: uuid.UUID | None = Query(None),
    tag_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """(Público) Retorna fotos aprovadas da barbearia."""
    service = GalleryService(db)
    return await service.list_approved_images(barber_id, tag_id)


@router.get("/tags", response_model=list[GalleryTagResponse])
async def list_tags(db: AsyncSession = Depends(get_db)):
    """(Público) Lista as tags visuais (filtros)."""
    service = GalleryService(db)
    return await service.list_tags()


# ── Endpoints Autenticados (Moderação) ───────────────────

@router.post("/tags", response_model=GalleryTagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    data: GalleryTagCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Cria uma nova tag para o sistema (ex: Degradê)."""
    service = GalleryService(db)
    try:
        return await service.create_tag(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=PortfolioImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    data: PortfolioImageCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_barber_or_admin)
):
    """(Barbeiro/Admin) Cadastra nova foto. Se for admin, já entra aprovada."""
    stmt = select(Barber.id).where(Barber.user_id == user.id)
    barber_id = (await db.execute(stmt)).scalar_one_or_none()
    
    if not barber_id:
        raise HTTPException(status_code=404, detail="Perfil de barbeiro não encontrado.")

    auto_approve = user.role == Role.ADMIN
    service = GalleryService(db)
    return await service.upload_image(barber_id, data, auto_approve)


@router.get("/pending", response_model=list[PortfolioImageResponse])
async def list_pending_images(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Lista fotos submetidas por barbeiros aguardando aprovação."""
    service = GalleryService(db)
    return await service.list_pending_images()


@router.put("/{image_id}/approve", response_model=PortfolioImageResponse)
async def approve_image(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Aprova uma foto para a galeria pública."""
    service = GalleryService(db)
    try:
        return await service.approve_image(image_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_barber_or_admin)
):
    """(Barbeiro/Admin) Exclui uma foto. Barbeiro só pode excluir as próprias."""
    service = GalleryService(db)
    
    requesting_barber_id = None
    if user.role != Role.ADMIN:
        stmt = select(Barber.id).where(Barber.user_id == user.id)
        requesting_barber_id = (await db.execute(stmt)).scalar_one_or_none()
        
    try:
        success = await service.delete_image(image_id, requesting_barber_id)
        if not success:
            raise HTTPException(status_code=404, detail="Imagem não encontrada.")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
