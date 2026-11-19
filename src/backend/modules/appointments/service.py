"""
Trim — Appointments Service

Lógica de negócio complexa de Agendamentos: motor de disponibilidade, 
prevenção de conflito e clonagem de dados financeiros.
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.config import settings
from src.backend.modules.appointments.models import Appointment, AppointmentItem, AppointmentStatus
from src.backend.modules.appointments.schemas import AppointmentCreateRequest
from src.backend.modules.barbers.models import WorkSchedule
from src.backend.modules.services.models import BarberServiceAssociation, Service


PAST_START_ERROR = "Não é possível agendar em um horário que já passou."
NOT_FOUND_ERROR = "Agendamento não encontrado."
CANCEL_STATUS_ERROR = "Só é possível cancelar agendamentos pendentes ou confirmados."
CANCEL_STARTED_ERROR = "Não é possível cancelar um agendamento que já começou."
CANCELLABLE_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)


def utc_now() -> datetime:
    """Instante atual em UTC. Os testes substituem esta função para fixar "agora"."""
    return datetime.now(timezone.utc)


class AppointmentService:
    def __init__(self, db: AsyncSession, now: Callable[[], datetime] | None = None):
        self.db = db
        self._now = now

    # ── Fuso da barbearia ────────────────────────────────
    # O WorkSchedule guarda horas locais; o banco guarda UTC (SPEC/2026-11-18-agendamento-fuso-horario.md).

    @property
    def shop_tz(self) -> ZoneInfo:
        return ZoneInfo(settings.shop_timezone)

    def now(self) -> datetime:
        return (self._now or utc_now)().astimezone(timezone.utc)

    def local_today(self) -> date:
        return self.now().astimezone(self.shop_tz).date()

    def _local_to_utc(self, day: date, at: time) -> datetime:
        return datetime.combine(day, at, tzinfo=self.shop_tz).astimezone(timezone.utc)

    def _to_utc(self, dt: datetime) -> datetime:
        """Sem fuso = horário da barbearia; com fuso = convertido para UTC."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.shop_tz)
        return dt.astimezone(timezone.utc)

    def _earliest_start(self) -> datetime:
        """Inícios até este instante (inclusive) não podem ser agendados."""
        return self.now() + timedelta(minutes=settings.booking_min_lead_minutes)

    def _last_bookable_date(self) -> date:
        return self.local_today() + timedelta(days=settings.booking_max_days_ahead)

    async def _get_services_for_barber(self, barber_id: uuid.UUID, service_ids: list[uuid.UUID]) -> list[Service]:
        """Garante que o barbeiro presta todos os serviços solicitados e retorna as instâncias."""
        stmt = (
            select(Service)
            .join(BarberServiceAssociation, Service.id == BarberServiceAssociation.service_id)
            .where(BarberServiceAssociation.barber_id == barber_id)
            .where(Service.id.in_(service_ids))
            .where(Service.is_active == True)
        )
        result = await self.db.execute(stmt)
        services = list(result.scalars().all())
        
        if len(services) != len(set(service_ids)):
            raise ValueError("Um ou mais serviços são inválidos ou não são prestados por este barbeiro.")
        return services

    async def _check_conflict(self, barber_id: uuid.UUID, start_dt: datetime, end_dt: datetime) -> bool:
        """Verifica se existe agendamento PENDING ou CONFIRMED sobrepondo o período desejado."""
        stmt = select(Appointment.id).where(
            Appointment.barber_id == barber_id,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED]),
            # A sobreposição ocorre se: (A_start < B_end) E (A_end > B_start)
            Appointment.start_datetime < end_dt,
            Appointment.end_datetime > start_dt
        )
        result = await self.db.execute(stmt)
        return result.first() is not None

    async def _get_schedule_for_date(self, barber_id: uuid.UUID, target_date: date) -> WorkSchedule | None:
        """Pega o WorkSchedule correspondente ao dia da semana."""
        day_of_week = target_date.weekday()
        # Python weekday: 0=Segunda, 6=Domingo.
        # Nosso banco (Padrão cron): 0=Domingo, 6=Sábado.
        db_day = (day_of_week + 1) % 7

        stmt = select(WorkSchedule).where(
            WorkSchedule.barber_id == barber_id,
            WorkSchedule.day_of_week == db_day
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_availability(self, barber_id: uuid.UUID, target_date: date, duration_minutes: int) -> list[str]:
        """Calcula slots livres ("HH:MM", hora local) para uma data no fuso da barbearia."""
        if not self.local_today() <= target_date <= self._last_bookable_date():
            return []

        schedule = await self._get_schedule_for_date(barber_id, target_date)
        
        if not schedule or not schedule.is_working:
            return []

        # Agendamentos do dia local: da meia-noite local até a meia-noite do dia seguinte
        start_of_day = self._local_to_utc(target_date, time.min)
        end_of_day = self._local_to_utc(target_date + timedelta(days=1), time.min)
        
        stmt = select(Appointment.start_datetime, Appointment.end_datetime).where(
            Appointment.barber_id == barber_id,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED]),
            Appointment.start_datetime >= start_of_day,
            Appointment.start_datetime < end_of_day
        )
        result = await self.db.execute(stmt)
        booked_intervals = result.all()

        available_slots = []
        
        # Gerar slots de 30 em 30 minutos desde start_time até end_time.
        # O expediente está em hora local; as comparações são feitas em UTC.
        current_dt = self._local_to_utc(target_date, schedule.start_time)
        end_dt_limit = self._local_to_utc(target_date, schedule.end_time)
        earliest_start = self._earliest_start()

        break_start_dt = None
        break_end_dt = None
        if schedule.break_start and schedule.break_end:
            break_start_dt = self._local_to_utc(target_date, schedule.break_start)
            break_end_dt = self._local_to_utc(target_date, schedule.break_end)

        while current_dt + timedelta(minutes=duration_minutes) <= end_dt_limit:
            slot_end_dt = current_dt + timedelta(minutes=duration_minutes)
            
            # Verifica colisão com almoço
            is_break_conflict = False
            if break_start_dt and break_end_dt:
                if current_dt < break_end_dt and slot_end_dt > break_start_dt:
                    is_break_conflict = True
            
            # Verifica colisão com agendamentos existentes
            is_booked_conflict = False
            for booked_start, booked_end in booked_intervals:
                if current_dt < booked_end and slot_end_dt > booked_start:
                    is_booked_conflict = True
                    break
            
            is_past = current_dt <= earliest_start

            if not is_break_conflict and not is_booked_conflict and not is_past:
                available_slots.append(current_dt.astimezone(self.shop_tz).strftime("%H:%M"))
            
            # Avança o ponteiro de 30 em 30 min
            current_dt += timedelta(minutes=30)

        return available_slots

    async def create_appointment(self, client_id: uuid.UUID, data: AppointmentCreateRequest) -> Appointment:
        """Cria um agendamento clonando preços e prevenindo conflitos."""
        # 1. Recupera os serviços e valida se o barbeiro faz eles
        services = await self._get_services_for_barber(data.barber_id, data.service_ids)
        
        # 2. Calcula duração total e data de fim
        total_duration = sum(s.duration_minutes for s in services)
        total_price = sum(float(s.price) for s in services)
        
        # Horário sem fuso é o da barbearia; no banco, sempre UTC.
        start_dt = self._to_utc(data.start_datetime)
        local_date = start_dt.astimezone(self.shop_tz).date()

        if start_dt <= self._earliest_start():
            raise ValueError(PAST_START_ERROR)
        if local_date > self._last_bookable_date():
            raise ValueError(
                f"Só é possível agendar até {settings.booking_max_days_ahead} dias à frente."
            )

        end_dt = start_dt + timedelta(minutes=total_duration)

        # 3. Verifica choque de horários na agenda do barbeiro
        if await self._check_conflict(data.barber_id, start_dt, end_dt):
            raise ValueError("Conflito de horário. O barbeiro já possui um agendamento nesse período.")

        # 4. Verifica se o barbeiro trabalha no dia (dia da semana local)
        schedule = await self._get_schedule_for_date(data.barber_id, local_date)
        if not schedule or not schedule.is_working:
            raise ValueError("O barbeiro não trabalha nesse dia.")

        # Cria a transação de agendamento
        appointment = Appointment(
            client_id=client_id,
            barber_id=data.barber_id,
            start_datetime=start_dt,
            end_datetime=end_dt,
            status=AppointmentStatus.CONFIRMED,
            total_price=total_price,
            notes=data.notes
        )
        self.db.add(appointment)
        await self.db.flush()

        # Cria os AppointmentItems com snapshot de preço e duração
        for service in services:
            item = AppointmentItem(
                appointment_id=appointment.id,
                service_id=service.id,
                service_name=service.name,
                locked_price=service.price,
                duration_minutes=service.duration_minutes
            )
            self.db.add(item)

        await self.db.commit()
        
        # Dá refresh carregando a relation `items`
        stmt = select(Appointment).where(Appointment.id == appointment.id).options(selectinload(Appointment.items))
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_client_appointments(self, client_id: uuid.UUID) -> list[Appointment]:
        """Lista agendamentos de um cliente."""
        stmt = select(Appointment).where(Appointment.client_id == client_id).options(selectinload(Appointment.items)).order_by(Appointment.start_datetime.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_barber_appointments(self, barber_id: uuid.UUID) -> list[Appointment]:
        """Lista agendamentos de um barbeiro."""
        stmt = select(Appointment).where(Appointment.barber_id == barber_id).options(selectinload(Appointment.items)).order_by(Appointment.start_datetime.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def cancel_by_client(self, appointment_id: uuid.UUID, client_id: uuid.UUID) -> Appointment:
        """Cancela um agendamento do próprio cliente, se ainda ativo e no futuro.

        Agendamento de outra pessoa levanta o mesmo LookupError de um id inexistente,
        para não revelar que ele existe (SPEC/2026-11-18-cancelamento-agendamento.md).
        """
        stmt = select(Appointment).where(Appointment.id == appointment_id).options(selectinload(Appointment.items))
        appointment = (await self.db.execute(stmt)).scalar_one_or_none()

        if not appointment or appointment.client_id != client_id:
            raise LookupError(NOT_FOUND_ERROR)
        if appointment.status not in CANCELLABLE_STATUSES:
            raise ValueError(CANCEL_STATUS_ERROR)
        if appointment.start_datetime <= self.now():
            raise ValueError(CANCEL_STARTED_ERROR)

        appointment.status = AppointmentStatus.CANCELLED
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def update_status(self, appointment_id: uuid.UUID, new_status: AppointmentStatus) -> Appointment | None:
        """Altera o status do agendamento (CANCELLED, COMPLETED, etc)."""
        stmt = select(Appointment).where(Appointment.id == appointment_id).options(selectinload(Appointment.items))
        result = await self.db.execute(stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            return None

        if new_status == AppointmentStatus.COMPLETED and appointment.status != AppointmentStatus.COMPLETED:
            from src.backend.modules.finance.models import Transaction, TransactionType, PaymentMethod, BarberCommission
            from src.backend.modules.barbers.models import Barber
            
            # Cria a transação de faturamento
            transaction = Transaction(
                type=TransactionType.APPOINTMENT,
                reference_id=appointment.id,
                amount=appointment.total_price,
                payment_method=PaymentMethod.CASH,  # Default para simplificar
                user_id=appointment.client_id
            )
            self.db.add(transaction)
            await self.db.flush()

            # Calcula e cria a comissão do barbeiro
            stmt_b = select(Barber.commission_rate).where(Barber.id == appointment.barber_id)
            rate = (await self.db.execute(stmt_b)).scalar_one()

            comm = BarberCommission(
                barber_id=appointment.barber_id,
                transaction_id=transaction.id,
                amount=float(appointment.total_price) * (float(rate) / 100.0),
                is_paid=False
            )
            self.db.add(comm)

        appointment.status = new_status
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
