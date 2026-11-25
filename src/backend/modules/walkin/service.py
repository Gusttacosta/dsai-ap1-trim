"""
Trim — Walk-in Service

Lógica de manipulação da fila de espera e integração com Agendamentos.
SPEC/2026-11-25-cliente-sem-conta.md (#69): cliente sem conta, IDs validados, agendamento com a
duração do serviço e "hoje" no fuso da barbearia.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone  # noqa: F401 (date: os testes do #70 o substituem)
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings
from src.backend.modules.appointments.models import Appointment, AppointmentItem, AppointmentStatus
from src.backend.modules.auth.guest import guest_user_id
from src.backend.modules.auth.models import User
from src.backend.modules.barbers.models import Barber
from src.backend.modules.services.models import Service
from src.backend.modules.walkin.models import WalkInQueue, WalkInStatus
from src.backend.modules.walkin.schemas import WalkInAssignRequest, WalkInCreateRequest


class NotFound(LookupError):
    """Um id informado não existe (vira 404 na rota)."""


def utc_now() -> datetime:
    """Instante atual em UTC. Os testes substituem esta função para fixar "agora"."""
    return datetime.now(timezone.utc)


class WalkInService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _today_bounds(self) -> tuple[datetime, datetime]:
        """Início e fim do dia de hoje no fuso da barbearia, em UTC. Antes, a fila comparava o
        date.today() do servidor com o dia no fuso da sessão do banco e "virava" às 21:00 (#69)."""
        tz = ZoneInfo(settings.shop_timezone)
        today = utc_now().astimezone(tz).date()
        start = datetime.combine(today, time.min, tzinfo=tz)
        end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=tz)
        return start.astimezone(timezone.utc), end.astimezone(timezone.utc)

    def _today(self):
        start, end = self._today_bounds()
        return WalkInQueue.joined_at >= start, WalkInQueue.joined_at < end

    async def _active_service(self, service_id: uuid.UUID) -> Service:
        service = await self.db.get(Service, service_id)
        if service is None or not service.is_active:
            raise NotFound("Serviço não encontrado ou inativo.")
        return service

    async def _active_barber(self, barber_id: uuid.UUID) -> Barber:
        barber = await self.db.get(Barber, barber_id)
        if barber is None or not barber.is_active:
            raise NotFound("Barbeiro não encontrado ou inativo.")
        return barber

    async def add_to_queue(self, data: WalkInCreateRequest) -> WalkInQueue:
        """Adiciona um cliente na fila do dia atual."""
        # IDs desconhecidos estouravam a FK no commit e respondiam 500 (#69).
        await self._active_service(data.requested_service_id)
        if data.requested_barber_id is not None:
            await self._active_barber(data.requested_barber_id)
        if data.user_id is not None and await self.db.get(User, data.user_id) is None:
            raise NotFound("Cliente não encontrado.")

        # Descobre a última posição da fila DE HOJE
        stmt = select(func.coalesce(func.max(WalkInQueue.position), 0)).where(*self._today())
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

    async def assign_to_barber(
        self, walkin_id: uuid.UUID, data: WalkInAssignRequest, acting_barber_id: uuid.UUID | None = None
    ) -> WalkInQueue:
        """Puxa o cliente da fila e cria um Agendamento em progresso.

        `acting_barber_id`: o barbeiro que pede, quando quem pede não é o admin. Ele só pode puxar
        o cliente para a própria cadeira (#69)."""
        stmt = select(WalkInQueue).where(WalkInQueue.id == walkin_id)
        walkin = (await self.db.execute(stmt)).scalar_one_or_none()

        if not walkin:
            raise ValueError("Registro na fila não encontrado.")

        if walkin.status != WalkInStatus.WAITING:
            raise ValueError(f"Este registro já está com status {walkin.status.value}.")

        if acting_barber_id is not None and data.barber_id != acting_barber_id:
            raise PermissionError("O barbeiro só pode puxar o cliente para a própria cadeira.")

        await self._active_barber(data.barber_id)
        service = await self.db.get(Service, walkin.requested_service_id)
        if service is None:
            raise ValueError("Serviço solicitado inválido.")

        now = utc_now()

        # 1. Atualiza a fila
        walkin.status = WalkInStatus.ATTENDING
        walkin.finished_at = now

        # 2. Cria o agendamento já na cadeira. Quem chega sem conta fica no usuário Visitante, e o
        # nome vai nas observações (#69). A duração do serviço bloqueia a agenda do barbeiro, e o
        # item guarda o serviço no histórico.
        client_id = walkin.user_id or await guest_user_id(self.db)
        appointment = Appointment(
            client_id=client_id,
            barber_id=data.barber_id,
            start_datetime=now,
            end_datetime=now + timedelta(minutes=service.duration_minutes),
            status=AppointmentStatus.CONFIRMED,
            total_price=service.price,
            notes=f"Fila de espera: {walkin.customer_name}",
            items=[
                AppointmentItem(
                    service_id=service.id,
                    service_name=service.name,
                    locked_price=service.price,
                    duration_minutes=service.duration_minutes,
                )
            ],
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
        walkin.finished_at = utc_now()
        await self.db.commit()
        await self.db.refresh(walkin)
        return walkin

    async def list_live_queue(self) -> list[WalkInQueue]:
        """Lista as pessoas esperando na fila hoje."""
        stmt = select(WalkInQueue).where(
            *self._today(),
            WalkInQueue.status == WalkInStatus.WAITING
        ).order_by(WalkInQueue.position.asc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
