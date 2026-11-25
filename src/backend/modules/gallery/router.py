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
from src.backend.modules.auth.models import UserRole, User
from src.backend.modules.barbers.models import Barber
from src.backend.modules.gallery.schemas import (
    GalleryTagCreateRequest,
    GalleryTagResponse,
    GalleryTagUpdateRequest,
    PortfolioImageCreateRequest,
    PortfolioImageRejectRequest,
    PortfolioImageResponse,
)
from src.backend.modules.gallery.service import GalleryService

router = APIRouter()

IMAGE_NOT_FOUND = "Imagem não encontrada."
TAG_NOT_FOUND = "Tag não encontrada."

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


@router.put("/tags/{tag_id}", response_model=GalleryTagResponse)
async def rename_tag(
    tag_id: uuid.UUID,
    data: GalleryTagUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Renomeia uma tag."""
    service = GalleryService(db)
    try:
        tag = await service.rename_tag(tag_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if tag is None:
        raise HTTPException(status_code=404, detail=TAG_NOT_FOUND)
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Apaga uma tag. As fotos continuam, sem ela."""
    if not await GalleryService(db).delete_tag(tag_id):
        raise HTTPException(status_code=404, detail=TAG_NOT_FOUND)


@router.post("", response_model=PortfolioImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    data: PortfolioImageCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_barber_or_admin)
):
    """(Barbeiro/Admin) Cadastra nova foto. Se for admin, já entra aprovada.

    O admin pode enviar em nome de qualquer barbeiro ativo (`barber_id`), mesmo sem perfil próprio;
    o barbeiro só envia para o próprio portfólio (#71)."""
    is_admin = user.role == UserRole.ADMIN
    stmt = select(Barber.id).where(Barber.user_id == user.id)
    own_barber_id = (await db.execute(stmt)).scalar_one_or_none()

    if is_admin and data.barber_id is not None:
        target = await db.get(Barber, data.barber_id)
        if target is None or not target.is_active:
            raise HTTPException(status_code=404, detail="Barbeiro não encontrado ou inativo.")
        barber_id = target.id
    elif not own_barber_id:
        if is_admin:
            raise HTTPException(status_code=400, detail="Informe o barbeiro da foto (barber_id).")
        raise HTTPException(status_code=404, detail="Perfil de barbeiro não encontrado.")
    elif data.barber_id is not None and data.barber_id != own_barber_id:
        raise HTTPException(status_code=403, detail="O barbeiro só envia fotos para o próprio portfólio.")
    else:
        barber_id = own_barber_id

    auto_approve = is_admin
    service = GalleryService(db)
    try:
        return await service.upload_image(barber_id, data, auto_approve)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


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


@router.put("/{image_id}/unapprove", response_model=PortfolioImageResponse)
async def unapprove_image(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Tira uma foto da galeria pública; ela volta para a moderação."""
    image = await GalleryService(db).unapprove_image(image_id)
    if image is None:
        raise HTTPException(status_code=404, detail=IMAGE_NOT_FOUND)
    return image


@router.put("/{image_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_image(
    image_id: uuid.UUID,
    data: PortfolioImageRejectRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Recusa uma foto pendente com um motivo, que chega ao barbeiro como notificação."""
    try:
        found = await GalleryService(db).reject_image(image_id, data.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not found:
        raise HTTPException(status_code=404, detail=IMAGE_NOT_FOUND)


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_barber_or_admin)
):
    """(Barbeiro/Admin) Exclui uma foto. Barbeiro só pode excluir as próprias."""
    service = GalleryService(db)
    
    is_admin = user.role == UserRole.ADMIN
    requesting_barber_id = None
    if not is_admin:
        stmt = select(Barber.id).where(Barber.user_id == user.id)
        requesting_barber_id = (await db.execute(stmt)).scalar_one_or_none()
        # Sem perfil, não há como conferir a posse (#71).
        if requesting_barber_id is None:
            raise HTTPException(status_code=403, detail="Perfil de barbeiro não encontrado.")

    try:
        success = await service.delete_image(image_id, requesting_barber_id, is_admin=is_admin)
        if not success:
            raise HTTPException(status_code=404, detail="Imagem não encontrada.")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
