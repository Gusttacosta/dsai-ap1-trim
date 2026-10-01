"""
Trim — Dashboard Service

Serviço de agregação de dados para os relatórios.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.auth.models import User
from src.backend.modules.barbers.models import Barber
from src.backend.modules.dashboard.schemas import BarberPerformanceResponse, DailyOverviewResponse, FinancialSummaryResponse
from src.backend.modules.expenses.models import Expense
from src.backend.modules.finance.models import BarberCommission, Transaction, TransactionType


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_financial_summary(self, start_date: date, end_date: date) -> FinancialSummaryResponse:
        """Calcula o Lucro Líquido baseado em Receitas, Comissões e Despesas."""
        
        # 1. Total de Receitas (Transactions) no período
        stmt_rev = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            func.date(Transaction.created_at) >= start_date,
            func.date(Transaction.created_at) <= end_date
        )
        total_revenue = (await self.db.execute(stmt_rev)).scalar_one()

        # 2. Total de Comissões geradas no período (pagas ou não, afetam a margem)
        stmt_com = select(func.coalesce(func.sum(BarberCommission.amount), 0)).where(
            func.date(BarberCommission.created_at) >= start_date,
            func.date(BarberCommission.created_at) <= end_date
        )
        total_commissions = (await self.db.execute(stmt_com)).scalar_one()

        # 3. Total de Despesas (Expenses) cuja data de PAGAMENTO está no período
        stmt_exp = select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.payment_date >= start_date,
            Expense.payment_date <= end_date
        )
        total_expenses = (await self.db.execute(stmt_exp)).scalar_one()

        net_profit = total_revenue - total_commissions - total_expenses

        return FinancialSummaryResponse(
            total_revenue=total_revenue,
            total_commissions=total_commissions,
            total_expenses=total_expenses,
            net_profit=net_profit
        )

    async def get_daily_overview(self, target_date: date) -> DailyOverviewResponse:
        """Visão operacional de um dia específico (por padrão, hoje)."""
        
        stmt_appointments = select(Appointment.status).where(func.date(Appointment.start_datetime) == target_date)
        result = await self.db.execute(stmt_appointments)
        statuses = result.scalars().all()

        total_appointments = len(statuses)
        completed = statuses.count(AppointmentStatus.COMPLETED)
        no_show = statuses.count(AppointmentStatus.NO_SHOW)
        cancelled = statuses.count(AppointmentStatus.CANCELLED)

        # Ticket médio das transações geradas HOJE (tipo APPOINTMENT)
        stmt_ticket = select(func.coalesce(func.avg(Transaction.amount), 0)).where(
            func.date(Transaction.created_at) == target_date,
            Transaction.type == TransactionType.APPOINTMENT
        )
        ticket_medio = (await self.db.execute(stmt_ticket)).scalar_one()

        return DailyOverviewResponse(
            total_appointments=total_appointments,
            completed_appointments=completed,
            no_show_appointments=no_show,
            cancelled_appointments=cancelled,
            ticket_medio=Decimal(str(round(ticket_medio, 2)))
        )

    async def get_barber_performance(self, barber_id: uuid.UUID, start_date: date, end_date: date) -> BarberPerformanceResponse:
        """Busca o desempenho de um único barbeiro."""
        
        # Nome do barbeiro
        stmt_name = select(User.name).select_from(Barber).join(User, Barber.user_id == User.id).where(Barber.id == barber_id)
        barber_name = (await self.db.execute(stmt_name)).scalar_one()

        # Atendimentos (COMPLETED)
        stmt_count = select(func.count(Appointment.id)).where(
            Appointment.barber_id == barber_id,
            Appointment.status == AppointmentStatus.COMPLETED,
            func.date(Appointment.start_datetime) >= start_date,
            func.date(Appointment.start_datetime) <= end_date
        )
        total_appointments = (await self.db.execute(stmt_count)).scalar_one()

        # Comissões geradas
        stmt_comm = select(func.coalesce(func.sum(BarberCommission.amount), 0)).where(
            BarberCommission.barber_id == barber_id,
            func.date(BarberCommission.created_at) >= start_date,
            func.date(BarberCommission.created_at) <= end_date
        )
        total_commission = (await self.db.execute(stmt_comm)).scalar_one()
        
        # Faturamento gerado (Join de Commission com Transaction para pegar o valor cheio pago pelo cliente)
        stmt_rev = select(func.coalesce(func.sum(Transaction.amount), 0)).select_from(BarberCommission).join(
            Transaction, BarberCommission.transaction_id == Transaction.id
        ).where(
            BarberCommission.barber_id == barber_id,
            func.date(BarberCommission.created_at) >= start_date,
            func.date(BarberCommission.created_at) <= end_date
        )
        total_revenue = (await self.db.execute(stmt_rev)).scalar_one()

        return BarberPerformanceResponse(
            barber_id=barber_id,
            barber_name=barber_name,
            total_appointments=total_appointments,
            total_revenue_generated=total_revenue,
            total_commission_earned=total_commission
        )

    async def get_barber_ranking(self, start_date: date, end_date: date) -> list[BarberPerformanceResponse]:
        """Calcula o desempenho de todos os barbeiros e retorna ordenado por faturamento gerado."""
        
        stmt = select(Barber.id)
        barbers = (await self.db.execute(stmt)).scalars().all()
        
        ranking = []
        for b_id in barbers:
            perf = await self.get_barber_performance(b_id, start_date, end_date)
            ranking.append(perf)
            
        # Ordena descrescente por receita gerada
        ranking.sort(key=lambda x: x.total_revenue_generated, reverse=True)
        return ranking
