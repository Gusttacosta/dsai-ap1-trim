"""
Trim — Walk-in Service

Lógica de manipulação da fila de espera e integração com Agendamentos.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.services.models import Service
from src.backend.modules.walkin.models import WalkInQueue, WalkInStatus
from src.backend.modules.walkin.schemas import WalkInAssignRequest, WalkInCreateRequest


class WalkInService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_to_queue(self, data: WalkInCreateRequest) -> WalkInQueue:
        """Adiciona um cliente na fila do dia atual."""
        today = date.today()

        # Descobre a última posição da fila DE HOJE
        stmt = select(func.coalesce(func.max(WalkInQueue.position), 0)).where(
            func.date(WalkInQueue.joined_at) == today
        )
        last_position = (await self.db.execute(stmt)).scalar_one()

        walkin = WalkInQueue(
            customer_name=data.customer_name,
            user_id=data.user_id,
            requested_service_id=data.requested_service_id,
            requested_barber_id=data.requested_barber_id,
            position=last_position + 1
        )
        self.db.add(walkin)
        await self.db.commit()
        await self.db.refresh(walkin)
        return walkin

    async def assign_to_barber(self, walkin_id: uuid.UUID, data: WalkInAssignRequest) -> WalkInQueue:
        """Puxa o cliente da fila e cria um Agendamento em progresso."""
        stmt = select(WalkInQueue).where(WalkInQueue.id == walkin_id)
        walkin = (await self.db.execute(stmt)).scalar_one_or_none()

        if not walkin:
            raise ValueError("Registro na fila não encontrado.")

        if walkin.status != WalkInStatus.WAITING:
            raise ValueError(f"Este registro já está com status {walkin.status.value}.")

        # Busca o preço do serviço para montar o agendamento
        stmt_svc = select(Service.price).where(Service.id == walkin.requested_service_id)
        service_price = (await self.db.execute(stmt_svc)).scalar_one_or_none()
        
        if service_price is None:
            raise ValueError("Serviço solicitado inválido.")

        now = datetime.now(timezone.utc)
        
        # 1. Atualiza a fila
        walkin.status = WalkInStatus.ATTENDING
        walkin.finished_at = now
        
        # 2. Cria o Agendamento Ativo (Pulou a agenda e foi direto pra cadeira)
        appointment = Appointment(
            client_id=walkin.user_id,
            barber_id=data.barber_id,
            start_datetime=now,
            end_datetime=now,  # Dummy, o ideal é prever com base na duração, mas no walkin ele já tá lá
            status=AppointmentStatus.CONFIRMED,
            total_price=service_price
        )
        self.db.add(appointment)
        await self.db.commit()
        
        # O caixa depois fará checkout desse appointment.id normalmente.
        await self.db.refresh(walkin)
        return walkin

    async def cancel_walkin(self, walkin_id: uuid.UUID) -> WalkInQueue:
        """Marca o cliente como desistente."""
        stmt = select(WalkInQueue).where(WalkInQueue.id == walkin_id)
        walkin = (await self.db.execute(stmt)).scalar_one_or_none()

        if not walkin:
            raise ValueError("Registro na fila não encontrado.")
            
        if walkin.status != WalkInStatus.WAITING:
            raise ValueError("Apenas registros aguardando podem ser cancelados.")

        walkin.status = WalkInStatus.CANCELLED
        walkin.finished_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(walkin)
        return walkin

    async def list_live_queue(self) -> list[WalkInQueue]:
        """Lista as pessoas esperando na fila hoje."""
        today = date.today()
        stmt = select(WalkInQueue).where(
            func.date(WalkInQueue.joined_at) == today,
            WalkInQueue.status == WalkInStatus.WAITING
        ).order_by(WalkInQueue.position.asc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
