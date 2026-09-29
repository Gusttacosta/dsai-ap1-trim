"""
Trim — Services Router

Endpoints REST para o Catálogo de Serviços e vínculos com Barbeiros.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin
from src.backend.modules.auth.models import User
from src.backend.modules.barbers.schemas import BarberPublicResponse
from src.backend.modules.services.schemas import (
    ServiceCreateRequest,
    ServiceResponse,
    ServiceUpdateRequest,
    ServiceWithBarbersResponse,
)
from src.backend.modules.services.service import CatalogService

router = APIRouter()

# ── Endpoints Públicos (Catálogo) ─────────────────────────

@router.get("", response_model=list[ServiceResponse], summary="Lista serviços ativos")
async def list_services(db: AsyncSession = Depends(get_db)):
    """Retorna todos os serviços disponíveis (is_active=True)."""
    service = CatalogService(db)
    return await service.list_active_services()


@router.get("/{service_id}", response_model=ServiceWithBarbersResponse, summary="Detalhes de um serviço e quem o realiza")
async def get_service(service_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retorna os detalhes de um serviço e a lista de barbeiros habilitados para ele."""
    service = CatalogService(db)
    srv = await service.get_service(service_id)
    if not srv or not srv.is_active:
        raise HTTPException(status_code=404, detail="Serviço não encontrado ou inativo.")
    
    barbers = await service.get_barbers_by_service(service_id)
    
    return ServiceWithBarbersResponse(
        id=srv.id,
        name=srv.name,
        description=srv.description,
        price=srv.price,
        duration_minutes=srv.duration_minutes,
        is_active=srv.is_active,
        created_at=srv.created_at,
        updated_at=srv.updated_at,
        barbers=barbers,
    )


@router.get("/barber/{barber_id}", response_model=list[ServiceResponse], summary="Serviços de um barbeiro")
async def get_barber_services(barber_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Lista os serviços que um barbeiro específico está habilitado a fazer."""
    service = CatalogService(db)
    return await service.get_services_by_barber(barber_id)


# ── Endpoints Administrativos ──────────────────────────────

@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Cria um novo serviço no catálogo."""
    service = CatalogService(db)
    try:
        return await service.create_service(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: uuid.UUID,
    data: ServiceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Atualiza dados de um serviço."""
    service = CatalogService(db)
    try:
        srv = await service.update_service(service_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not srv:
        raise HTTPException(status_code=404, detail="Serviço não encontrado.")
    return srv


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_service(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Desativa um serviço (soft delete)."""
    service = CatalogService(db)
    success = await service.deactivate_service(service_id)
    if not success:
        raise HTTPException(status_code=404, detail="Serviço não encontrado.")


@router.post("/{service_id}/barbers/{barber_id}", status_code=status.HTTP_201_CREATED)
async def link_barber_to_service(
    service_id: uuid.UUID,
    barber_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Vincula um serviço a um barbeiro."""
    service = CatalogService(db)
    success = await service.link_barber_to_service(barber_id, service_id)
    if not success:
        # Aqui pode ser falha por FK inexistente ou porque já existe o vínculo.
        # Retornamos 400 para manter simples e amigável conforme a Spec.
        raise HTTPException(
            status_code=400, 
            detail="Não foi possível vincular. Verifique se o barbeiro/serviço existem ou se já estão vinculados."
        )
    return {"message": "Vínculo criado com sucesso."}


@router.delete("/{service_id}/barbers/{barber_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_barber_from_service(
    service_id: uuid.UUID,
    barber_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Desvincula um barbeiro de um serviço."""
    service = CatalogService(db)
    success = await service.unlink_barber_from_service(barber_id, service_id)
    if not success:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
