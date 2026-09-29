"""
Trim — Expenses Router

Endpoints para registro de despesas e saídas do caixa.
Todos os endpoints são restritos ao perfil de Admin.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin
from src.backend.modules.auth.models import User
from src.backend.modules.expenses.schemas import (
    ExpenseCategoryCreateRequest,
    ExpenseCategoryResponse,
    ExpenseCreateRequest,
    ExpenseResponse,
    ExpenseUpdateRequest,
)
from src.backend.modules.expenses.service import ExpenseService

router = APIRouter()


# ── Categorias ───────────────────────────────────────────

@router.get("/categories", response_model=list[ExpenseCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Lista as categorias de despesa."""
    service = ExpenseService(db)
    return await service.list_categories()


@router.post("/categories", response_model=ExpenseCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: ExpenseCategoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Cria uma nova categoria."""
    service = ExpenseService(db)
    try:
        return await service.create_category(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Despesas ─────────────────────────────────────────────

@router.get("", response_model=list[ExpenseResponse])
async def list_expenses(
    start_date: date | None = Query(None, description="Filtrar a partir desta data"),
    end_date: date | None = Query(None, description="Filtrar até esta data"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Retorna as despesas pagas (com filtro opcional de data)."""
    service = ExpenseService(db)
    return await service.list_expenses(start_date, end_date)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Registra o pagamento de uma despesa."""
    service = ExpenseService(db)
    try:
        return await service.create_expense(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: uuid.UUID,
    data: ExpenseUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Altera um lançamento de despesa."""
    service = ExpenseService(db)
    try:
        expense = await service.update_expense(expense_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not expense:
        raise HTTPException(status_code=404, detail="Despesa não encontrada.")
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Remove o registro de uma despesa (ex: lançamento duplicado)."""
    service = ExpenseService(db)
    success = await service.delete_expense(expense_id)
    if not success:
        raise HTTPException(status_code=404, detail="Despesa não encontrada.")
