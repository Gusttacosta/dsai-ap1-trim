"""
Trim — Products Router

Endpoints REST para o Catálogo de Produtos e Gestão de Estoque.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin
from src.backend.modules.auth.models import User
from src.backend.modules.products.schemas import (
    InventoryMovementRequest,
    InventoryMovementResponse,
    ProductAdminResponse,
    ProductCreateRequest,
    ProductPublicResponse,
    ProductUpdateRequest,
)
from src.backend.modules.products.service import ProductService

router = APIRouter()

# ── Endpoints Públicos (Clientes) ────────────────────────

@router.get("", response_model=list[ProductPublicResponse], summary="Vitrine de Produtos")
async def list_public_products(
    show_out_of_stock: bool = Query(False, description="Exibir produtos sem estoque?"),
    db: AsyncSession = Depends(get_db)
):
    """Retorna os produtos ativos para a vitrine (omite custo e dados sensíveis)."""
    service = ProductService(db)
    return await service.list_public_products(show_out_of_stock=show_out_of_stock)

@router.get("/{product_id}", response_model=ProductPublicResponse)
async def get_public_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Detalhes de um produto específico para clientes."""
    service = ProductService(db)
    product = await service.get_product(product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Produto não encontrado ou indisponível.")
    return product


# ── Endpoints Administrativos ─────────────────────────────

@router.get("/admin/all", response_model=list[ProductAdminResponse], summary="Lista Completa Admin")
async def list_admin_products(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Retorna todos os produtos com dados sensíveis de custo e inativos."""
    service = ProductService(db)
    return await service.list_admin_products()


@router.post("", response_model=ProductAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Cadastra um novo produto (inicia com estoque 0)."""
    service = ProductService(db)
    try:
        return await service.create_product(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{product_id}", response_model=ProductAdminResponse)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Edita dados de um produto (exceto o estoque, que é via movimentação)."""
    service = ProductService(db)
    try:
        product = await service.update_product(product_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Desativa um produto do catálogo."""
    service = ProductService(db)
    success = await service.deactivate_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")


# ── Inventário (Estoque) ──────────────────────────────────

@router.post("/{product_id}/inventory", response_model=ProductAdminResponse)
async def register_inventory_movement(
    product_id: uuid.UUID,
    data: InventoryMovementRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Registra uma entrada ou saída de estoque para um produto."""
    service = ProductService(db)
    try:
        # Passa o ID do Admin que está fazendo a operação
        return await service.register_movement(product_id, admin.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{product_id}/inventory", response_model=list[InventoryMovementResponse])
async def get_inventory_history(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """(Admin) Retorna a trilha de auditoria (histórico) do estoque de um produto."""
    service = ProductService(db)
    
    # Valida se produto existe primeiro
    product = await service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    return await service.get_product_movements(product_id)
