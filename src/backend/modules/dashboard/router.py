"""
Trim — Dashboard Router

Endpoints para consultar métricas, faturamento e desempenho da barbearia.
"""

from datetime import date
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.modules.auth.dependencies import get_current_admin, get_current_barber_or_admin
from src.backend.modules.auth.models import User
from src.backend.modules.barbers.models import Barber
from src.backend.modules.dashboard.schemas import BarberPerformanceResponse, DailyOverviewResponse, FinancialSummaryResponse
from src.backend.modules.dashboard.service import DashboardService, month_of, shop_today

router = APIRouter()


def get_month_boundaries() -> tuple[date, date]:
    """Primeiro e último dia do mês corrente da barbearia, quando as datas não vêm (#67)."""
    return month_of(shop_today())


def period(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    s_date, e_date = get_month_boundaries()
    start_date, end_date = start_date or s_date, end_date or e_date
    if start_date > end_date:
        # Antes, um período invertido devolvia zeros sem aviso (#67).
        raise HTTPException(status_code=422, detail="A data inicial não pode ser depois da data final.")
    return start_date, end_date


@router.get("/financial-summary", response_model=FinancialSummaryResponse)
async def get_financial_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Retorna Receita, Despesas, Comissões e Lucro Líquido do período."""
    start_date, end_date = period(start_date, end_date)

    service = DashboardService(db)
    return await service.get_financial_summary(start_date, end_date)


@router.get("/daily-overview", response_model=DailyOverviewResponse)
async def get_daily_overview(
    target_date: date | None = Query(None, description="Padrão é 'hoje'"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Visão operacional de um dia (Ocupação, Ticket médio)."""
    target = target_date or shop_today()
    service = DashboardService(db)
    return await service.get_daily_overview(target)


@router.get("/barber-ranking", response_model=list[BarberPerformanceResponse])
async def get_barber_ranking(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Lista os barbeiros ativos ordenados por faturamento gerado."""
    start_date, end_date = period(start_date, end_date)

    service = DashboardService(db)
    return await service.get_barber_ranking(start_date, end_date)


@router.get("/me", response_model=BarberPerformanceResponse)
async def get_my_performance(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    barber_user: User = Depends(get_current_barber_or_admin)
):
    """(Barbeiro) Retorna apenas o desempenho do barbeiro logado."""
    start_date, end_date = period(start_date, end_date)

    stmt = select(Barber.id).where(Barber.user_id == barber_user.id)
    barber_id = (await db.execute(stmt)).scalar_one_or_none()
    
    if not barber_id:
        raise HTTPException(status_code=404, detail="Perfil de barbeiro não encontrado.")

    service = DashboardService(db)
    return await service.get_barber_performance(barber_id, start_date, end_date)
