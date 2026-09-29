"""
Trim — Dashboard Schemas

Schemas de retorno para os relatórios e indicadores da barbearia.
"""

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FinancialSummaryResponse(BaseModel):
    """Resumo financeiro consolidado do Admin."""
    model_config = ConfigDict(from_attributes=True)
    
    total_revenue: Decimal
    total_commissions: Decimal
    total_expenses: Decimal
    net_profit: Decimal


class DailyOverviewResponse(BaseModel):
    """Visão operacional do dia."""
    model_config = ConfigDict(from_attributes=True)
    
    total_appointments: int
    completed_appointments: int
    no_show_appointments: int
    cancelled_appointments: int
    ticket_medio: Decimal


class BarberPerformanceResponse(BaseModel):
    """Desempenho individual de um barbeiro (usado no ranking e painel individual)."""
    model_config = ConfigDict(from_attributes=True)
    
    barber_id: uuid.UUID
    barber_name: str
    total_appointments: int
    total_revenue_generated: Decimal
    total_commission_earned: Decimal
