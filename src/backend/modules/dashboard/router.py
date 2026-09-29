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
from src.backend.modules.dashboard.service import DashboardService

router = APIRouter()


def get_month_boundaries() -> tuple[date, date]:
    """Utilitário: Retorna o primeiro e último dia do mês corrente caso as datas não sejam passadas."""
    from calendar import monthrange
    today = date.today()
    start_date = today.replace(day=1)
    end_date = today.replace(day=monthrange(today.year, today.month)[1])
    return start_date, end_date


@router.get("/financial-summary", response_model=FinancialSummaryResponse)
async def get_financial_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Retorna Receita, Despesas, Comissões e Lucro Líquido do período."""
    s_date, e_date = get_month_boundaries()
    start_date = start_date or s_date
    end_date = end_date or e_date

    service = DashboardService(db)
    return await service.get_financial_summary(start_date, end_date)


@router.get("/daily-overview", response_model=DailyOverviewResponse)
async def get_daily_overview(
    target_date: date | None = Query(None, description="Padrão é 'hoje'"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Visão operacional de um dia (Ocupação, Ticket médio)."""
    target = target_date or date.today()
    service = DashboardService(db)
    return await service.get_daily_overview(target)


@router.get("/barber-ranking", response_model=list[BarberPerformanceResponse])
async def get_barber_ranking(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """(Admin) Lista barbeiros ordenados por faturamento gerado."""
    s_date, e_date = get_month_boundaries()
    start_date = start_date or s_date
    end_date = end_date or e_date

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
    s_date, e_date = get_month_boundaries()
    start_date = start_date or s_date
    end_date = end_date or e_date

    stmt = select(Barber.id).where(Barber.user_id == barber_user.id)
    barber_id = (await db.execute(stmt)).scalar_one_or_none()
    
    if not barber_id:
        raise HTTPException(status_code=404, detail="Perfil de barbeiro não encontrado.")

    service = DashboardService(db)
    return await service.get_barber_performance(barber_id, start_date, end_date)
