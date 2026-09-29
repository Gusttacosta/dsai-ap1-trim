"""
Trim — Expenses Service

Regras de negócio e operações de banco para controle de despesas.
"""

import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.modules.expenses.models import Expense, ExpenseCategory
from src.backend.modules.expenses.schemas import (
    ExpenseCategoryCreateRequest,
    ExpenseCreateRequest,
    ExpenseUpdateRequest,
)


class ExpenseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Categorias ───────────────────────────────────────────

    async def create_category(self, data: ExpenseCategoryCreateRequest) -> ExpenseCategory:
        """Cria uma nova categoria (nome único)."""
        stmt = select(ExpenseCategory).where(ExpenseCategory.name == data.name)
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ValueError(f"Já existe uma categoria chamada '{data.name}'.")

        category = ExpenseCategory(name=data.name)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def list_categories(self) -> list[ExpenseCategory]:
        """Lista todas as categorias."""
        stmt = select(ExpenseCategory).order_by(ExpenseCategory.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    # ── Despesas ─────────────────────────────────────────────

    async def create_expense(self, data: ExpenseCreateRequest) -> Expense:
        """Registra uma nova despesa paga."""
        if data.category_id:
            stmt = select(ExpenseCategory.id).where(ExpenseCategory.id == data.category_id)
            if not (await self.db.execute(stmt)).scalar_one_or_none():
                raise ValueError("Categoria informada não existe.")

        expense = Expense(**data.model_dump())
        self.db.add(expense)
        await self.db.commit()

        # Recarrega a despesa para trazer a relação 'category' montada
        stmt = select(Expense).where(Expense.id == expense.id).options(selectinload(Expense.category))
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def update_expense(self, expense_id: uuid.UUID, data: ExpenseUpdateRequest) -> Expense | None:
        """Edita dados de uma despesa lançada."""
        stmt = select(Expense).where(Expense.id == expense_id)
        expense = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not expense:
            return None

        if data.category_id is not None:
            stmt_cat = select(ExpenseCategory.id).where(ExpenseCategory.id == data.category_id)
            if not (await self.db.execute(stmt_cat)).scalar_one_or_none():
                raise ValueError("Categoria informada não existe.")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(expense, key, value)

        await self.db.commit()
        
        stmt_refresh = select(Expense).where(Expense.id == expense.id).options(selectinload(Expense.category))
        result = await self.db.execute(stmt_refresh)
        return result.scalar_one()

    async def delete_expense(self, expense_id: uuid.UUID) -> bool:
        """Remove fisicamente o registro de despesa."""
        stmt = delete(Expense).where(Expense.id == expense_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def list_expenses(self, start_date: date | None = None, end_date: date | None = None) -> list[Expense]:
        """Lista as despesas com filtro opcional de data."""
        stmt = select(Expense).options(selectinload(Expense.category))
        
        if start_date:
            stmt = stmt.where(Expense.payment_date >= start_date)
        if end_date:
            stmt = stmt.where(Expense.payment_date <= end_date)
            
        stmt = stmt.order_by(Expense.payment_date.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
