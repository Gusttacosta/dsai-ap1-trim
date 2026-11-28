"""
Trim — Dashboard Service

Serviço de agregação de dados para os relatórios.

SPEC/2026-11-25-relatorios.md (#67): os dias e os meses são os da barbearia
(`settings.shop_timezone`), convertidos para UTC antes de filtrar; o faturamento do dia volta na
resposta; o ranking só tem barbeiros ativos e é calculado com consultas agrupadas; e a visão do dia
traz a ocupação da agenda.
"""

import uuid
from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings
from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.auth.models import User
from src.backend.modules.barbers.models import Barber, WorkSchedule
from src.backend.modules.dashboard.schemas import BarberPerformanceResponse, DailyOverviewResponse, FinancialSummaryResponse
from src.backend.modules.expenses.models import Expense
from src.backend.modules.finance.models import BarberCommission, Transaction, TransactionType

CENTS = Decimal("0.01")
# Status que ocupam a agenda do barbeiro (os mesmos da disponibilidade).
BOOKED = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED)


def utc_now() -> datetime:
    """Instante atual em UTC. Os testes substituem esta função para fixar "hoje"."""
    return datetime.now(timezone.utc)


def shop_tz() -> ZoneInfo:
    return ZoneInfo(settings.shop_timezone)


def shop_today() -> date:
    return utc_now().astimezone(shop_tz()).date()


def month_of(day: date) -> tuple[date, date]:
    return day.replace(day=1), day.replace(day=monthrange(day.year, day.month)[1])


def utc_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """Do início de `start_date` ao início do dia seguinte a `end_date`, no fuso da barbearia."""
    tz = shop_tz()
    start = datetime.combine(start_date, time.min, tzinfo=tz)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def in_period(column, start_date: date, end_date: date):
    start, end = utc_bounds(start_date, end_date)
    return column >= start, column < end


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENTS)


def minutes_between(start: time, end: time) -> int:
    return (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_financial_summary(self, start_date: date, end_date: date) -> FinancialSummaryResponse:
        """Calcula o Lucro Líquido baseado em Receitas, Comissões e Despesas."""

        # 1. Total de Receitas (Transactions) no período
        stmt_rev = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            *in_period(Transaction.created_at, start_date, end_date)
        )
        total_revenue = (await self.db.execute(stmt_rev)).scalar_one()

        # 2. Total de Comissões geradas no período (pagas ou não, afetam a margem)
        stmt_com = select(func.coalesce(func.sum(BarberCommission.amount), 0)).where(
            *in_period(BarberCommission.created_at, start_date, end_date)
        )
        total_commissions = (await self.db.execute(stmt_com)).scalar_one()

        # 3. Total de Despesas (Expenses) cuja data de PAGAMENTO está no período (já é um dia local)
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
        """Visão operacional de um dia: atendimentos, ticket médio, faturamento e ocupação."""
        day = in_period(Appointment.start_datetime, target_date, target_date)
        rows = (await self.db.execute(
            select(Appointment.status, Appointment.start_datetime, Appointment.end_datetime).where(*day)
        )).all()
        statuses = [status for status, _, _ in rows]

        # Ticket médio das cobranças de atendimento do dia
        stmt_ticket = select(func.coalesce(func.avg(Transaction.amount), 0)).where(
            *in_period(Transaction.created_at, target_date, target_date),
            Transaction.type == TransactionType.APPOINTMENT
        )
        ticket_medio = (await self.db.execute(stmt_ticket)).scalar_one()

        # Faturamento total do dia: antes era calculado e descartado pelo schema (#67)
        stmt_rev = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            *in_period(Transaction.created_at, target_date, target_date)
        )
        total_revenue = (await self.db.execute(stmt_rev)).scalar_one()

        booked = sum(
            int((end - start).total_seconds() // 60) for status, start, end in rows if status in BOOKED
        )
        available = await self._available_minutes(target_date)
        occupancy = Decimal(booked * 100) / Decimal(available) if available else Decimal(0)

        return DailyOverviewResponse(
            total_appointments=len(statuses),
            completed_appointments=statuses.count(AppointmentStatus.COMPLETED),
            no_show_appointments=statuses.count(AppointmentStatus.NO_SHOW),
            cancelled_appointments=statuses.count(AppointmentStatus.CANCELLED),
            ticket_medio=money(ticket_medio),
            total_revenue=money(total_revenue),
            booked_minutes=booked,
            available_minutes=available,
            occupancy_rate=occupancy.quantize(CENTS),
        )

    async def _available_minutes(self, day: date) -> int:
        """Minutos de expediente dos barbeiros ativos no dia, sem o almoço."""
        day_of_week = (day.weekday() + 1) % 7  # o WorkSchedule começa no domingo (0)
        stmt = (
            select(WorkSchedule.start_time, WorkSchedule.end_time, WorkSchedule.break_start, WorkSchedule.break_end)
            .join(Barber, WorkSchedule.barber_id == Barber.id)
            .join(User, Barber.user_id == User.id)
            .where(
                WorkSchedule.day_of_week == day_of_week,
                WorkSchedule.is_working.is_(True),
                Barber.is_active.is_(True),
                User.is_active.is_(True),
            )
        )
        total = 0
        for start, end, break_start, break_end in (await self.db.execute(stmt)).all():
            total += minutes_between(start, end)
            if break_start and break_end:
                total -= minutes_between(break_start, break_end)
        return max(total, 0)

    async def _performance(
        self, start_date: date, end_date: date, barber_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, Decimal, Decimal]]:
        """Atendimentos concluídos, faturamento e comissões por barbeiro, com 3 consultas agrupadas
        no total, em vez de 3 por barbeiro (#67)."""
        if not barber_ids:
            return {}
        done = dict((await self.db.execute(
            select(Appointment.barber_id, func.count(Appointment.id))
            .where(
                Appointment.barber_id.in_(barber_ids),
                Appointment.status == AppointmentStatus.COMPLETED,
                *in_period(Appointment.start_datetime, start_date, end_date),
            )
            .group_by(Appointment.barber_id)
        )).all())
        commission_period = in_period(BarberCommission.created_at, start_date, end_date)
        commissions = dict((await self.db.execute(
            select(BarberCommission.barber_id, func.sum(BarberCommission.amount))
            .where(BarberCommission.barber_id.in_(barber_ids), *commission_period)
            .group_by(BarberCommission.barber_id)
        )).all())
        revenue = dict((await self.db.execute(
            select(BarberCommission.barber_id, func.sum(Transaction.amount))
            .join(Transaction, BarberCommission.transaction_id == Transaction.id)
            .where(BarberCommission.barber_id.in_(barber_ids), *commission_period)
            .group_by(BarberCommission.barber_id)
        )).all())
        return {
            b: (done.get(b, 0), revenue.get(b, Decimal(0)), commissions.get(b, Decimal(0)))
            for b in barber_ids
        }

    async def get_barber_performance(self, barber_id: uuid.UUID, start_date: date, end_date: date) -> BarberPerformanceResponse:
        """Busca o desempenho de um único barbeiro."""
        stmt_name = select(User.full_name).select_from(Barber).join(User, Barber.user_id == User.id).where(Barber.id == barber_id)
        barber_name = (await self.db.execute(stmt_name)).scalar_one()
        count, revenue, commission = (await self._performance(start_date, end_date, [barber_id]))[barber_id]
        return BarberPerformanceResponse(
            barber_id=barber_id,
            barber_name=barber_name,
            total_appointments=count,
            total_revenue_generated=revenue,
            total_commission_earned=commission
        )

    async def get_barber_ranking(self, start_date: date, end_date: date) -> list[BarberPerformanceResponse]:
        """Desempenho dos barbeiros ativos, do maior faturamento para o menor (#67)."""
        stmt = (
            select(Barber.id, User.full_name)
            .join(User, Barber.user_id == User.id)
            .where(Barber.is_active.is_(True), User.is_active.is_(True))
        )
        barbers = (await self.db.execute(stmt)).all()
        numbers = await self._performance(start_date, end_date, [b for b, _ in barbers])
        ranking = [
            BarberPerformanceResponse(
                barber_id=b,
                barber_name=name,
                total_appointments=numbers[b][0],
                total_revenue_generated=numbers[b][1],
                total_commission_earned=numbers[b][2],
            )
            for b, name in barbers
        ]
        ranking.sort(key=lambda x: (-x.total_revenue_generated, x.barber_name))
        return ranking
