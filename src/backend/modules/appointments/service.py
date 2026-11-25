"""
Trim — Appointments Service

Lógica de negócio complexa de Agendamentos: motor de disponibilidade, 
prevenção de conflito e clonagem de dados financeiros.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.config import settings
from src.backend.modules.appointments.models import Appointment, AppointmentItem, AppointmentStatus
from src.backend.modules.appointments.schemas import AppointmentCreateRequest
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber, WorkSchedule
from src.backend.modules.notifications.models import NotificationType
from src.backend.modules.notifications.service import notify
from src.backend.modules.services.models import BarberServiceAssociation, Service


PAST_START_ERROR = "Não é possível agendar em um horário que já passou."
NOT_FOUND_ERROR = "Agendamento não encontrado."
CANCEL_STATUS_ERROR = "Só é possível cancelar agendamentos pendentes ou confirmados."
CANCEL_STARTED_ERROR = "Não é possível cancelar um agendamento que já começou."
CANCELLABLE_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
BARBER_UNAVAILABLE_ERROR = "Barbeiro indisponível para agendamento."


class BarberUnavailable(ValueError):
    """Barbeiro desconhecido, ou com o perfil ou a conta desativados."""
FINISH_BEFORE_START_ERROR = "Só é possível concluir ou marcar falta depois do início do agendamento."

# Transições que barbeiro e admin podem fazer (SPEC/2026-11-18-status-agendamento.md).
# COMPLETED, NO_SHOW e CANCELLED são finais.
STAFF_TRANSITIONS = {
    AppointmentStatus.PENDING: {AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED},
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.NO_SHOW,
        AppointmentStatus.CANCELLED,
    },
}
AFTER_START_STATUSES = {AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW}

# Avisos ao cliente quando a barbearia muda o status (#75).
APPOINTMENT_NOTICE = NotificationType.APPOINTMENT_REMINDER
STATUS_NOTICES = {
    AppointmentStatus.CONFIRMED: ("Agendamento confirmado", "Seu horário de {when} foi confirmado."),
    AppointmentStatus.CANCELLED: ("Agendamento cancelado", "A barbearia cancelou o seu horário de {when}."),
    AppointmentStatus.COMPLETED: ("Atendimento concluído", "Obrigado pela visita de {when}!"),
}


@dataclass(frozen=True)
class WorkWindow:
    """Expediente de um dia convertido para UTC (o WorkSchedule guarda hora local)."""

    opens: datetime
    closes: datetime
    break_start: datetime | None
    break_end: datetime | None

    def overlaps_break(self, start: datetime, end: datetime) -> bool:
        if self.break_start is None or self.break_end is None:
            return False
        return start < self.break_end and end > self.break_start


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

    def _work_window(self, schedule: WorkSchedule, day: date) -> WorkWindow:
        has_break = schedule.break_start is not None and schedule.break_end is not None
        return WorkWindow(
            opens=self._local_to_utc(day, schedule.start_time),
            closes=self._local_to_utc(day, schedule.end_time),
            break_start=self._local_to_utc(day, schedule.break_start) if has_break else None,
            break_end=self._local_to_utc(day, schedule.break_end) if has_break else None,
        )

    def _schedule_error(self, schedule: WorkSchedule, day: date, start: datetime, end: datetime) -> str | None:
        """Mensagem de recusa se o atendimento não cabe no expediente ou encosta no almoço (#23)."""
        window = self._work_window(schedule, day)
        if start < window.opens or end > window.closes:
            return (
                "Horário fora do expediente do barbeiro nesse dia "
                f"({schedule.start_time:%H:%M} às {schedule.end_time:%H:%M})."
            )
        if window.overlaps_break(start, end):
            return (
                "Horário cai no intervalo de almoço do barbeiro "
                f"({schedule.break_start:%H:%M} às {schedule.break_end:%H:%M})."
            )
        return None

    async def _ensure_barber_available(self, barber_id: uuid.UUID) -> None:
        """Só barbeiro com o perfil e a conta ativos recebe agendamento."""
        stmt = (
            select(Barber.id)
            .join(User, Barber.user_id == User.id)
            .where(Barber.id == barber_id, Barber.is_active.is_(True), User.is_active.is_(True))
        )
        if (await self.db.execute(stmt)).scalar_one_or_none() is None:
            raise BarberUnavailable(BARBER_UNAVAILABLE_ERROR)

    async def get_availability(self, barber_id: uuid.UUID, target_date: date, duration_minutes: int) -> list[str]:
        """Calcula slots livres ("HH:MM", hora local) para uma data no fuso da barbearia."""
        await self._ensure_barber_available(barber_id)
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
        window = self._work_window(schedule, target_date)
        current_dt = window.opens
        earliest_start = self._earliest_start()

        while current_dt + timedelta(minutes=duration_minutes) <= window.closes:
            slot_end_dt = current_dt + timedelta(minutes=duration_minutes)

            # Verifica colisão com almoço
            is_break_conflict = window.overlaps_break(current_dt, slot_end_dt)

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
        await self._ensure_barber_available(data.barber_id)
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

        # 5. O atendimento inteiro precisa caber no expediente, fora do almoço (#23)
        schedule_error = self._schedule_error(schedule, local_date, start_dt, end_dt)
        if schedule_error:
            raise ValueError(schedule_error)

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

        # Avisos (#75): o cliente recebe a confirmação do pedido, e o barbeiro, o novo horário.
        when = self._when(appointment.start_datetime)
        await notify(self.db, client_id, "Agendamento recebido", f"Seu horário de {when} foi registrado.", APPOINTMENT_NOTICE)
        await self._notify_barber(appointment.barber_id, "Novo agendamento", f"Você tem um novo horário em {when}.")

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
        await self._notify_barber(
            appointment.barber_id, "Agendamento cancelado",
            f"O cliente cancelou o horário de {self._when(appointment.start_datetime)}.",
        )
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    def _when(self, start: datetime) -> str:
        return start.astimezone(self.shop_tz).strftime("%d/%m às %H:%M")

    async def _notify_barber(self, barber_id: uuid.UUID, title: str, message: str) -> None:
        user_id = (await self.db.execute(select(Barber.user_id).where(Barber.id == barber_id))).scalar_one_or_none()
        if user_id is not None:
            await notify(self.db, user_id, title, message, APPOINTMENT_NOTICE)

    async def change_status_by_staff(
        self, appointment_id: uuid.UUID, new_status: AppointmentStatus, user: User
    ) -> Appointment:
        """Barbeiro (só os próprios agendamentos) ou admin muda o status, se a transição for válida.

        Agendamento de outro barbeiro levanta o mesmo LookupError de um id inexistente.
        """
        stmt = select(Appointment).where(Appointment.id == appointment_id).options(selectinload(Appointment.items))
        appointment = (await self.db.execute(stmt)).scalar_one_or_none()
        if not appointment:
            raise LookupError(NOT_FOUND_ERROR)

        if user.role != UserRole.ADMIN:
            own_barber_id = (
                await self.db.execute(select(Barber.id).where(Barber.user_id == user.id))
            ).scalar_one_or_none()
            if appointment.barber_id != own_barber_id:
                raise LookupError(NOT_FOUND_ERROR)

        current = appointment.status
        if new_status not in STAFF_TRANSITIONS.get(current, set()):
            raise ValueError(f"Transição de status inválida: {current.value} → {new_status.value}.")

        started = appointment.start_datetime <= self.now()
        if new_status in AFTER_START_STATUSES and not started:
            raise ValueError(FINISH_BEFORE_START_ERROR)
        if new_status == AppointmentStatus.CANCELLED and started:
            raise ValueError(CANCEL_STARTED_ERROR)

        if new_status == AppointmentStatus.COMPLETED:
            await self._charge_once(appointment)

        appointment.status = new_status
        # O cliente fica sabendo das mudanças feitas pela barbearia (#75).
        if new_status in STATUS_NOTICES:
            title, text = STATUS_NOTICES[new_status]
            await notify(
                self.db, appointment.client_id, title, text.format(when=self._when(appointment.start_datetime)),
                APPOINTMENT_NOTICE,
            )
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def _charge_once(self, appointment: Appointment) -> None:
        """Cria a transação e a comissão do atendimento, se ainda não existir cobrança para ele."""
        from src.backend.modules.finance.models import BarberCommission, PaymentMethod, Transaction, TransactionType

        already_charged = (
            await self.db.execute(
                select(Transaction.id).where(
                    Transaction.type == TransactionType.APPOINTMENT,
                    Transaction.reference_id == appointment.id,
                )
            )
        ).first()
        if already_charged:
            return

        transaction = Transaction(
            type=TransactionType.APPOINTMENT,
            reference_id=appointment.id,
            amount=appointment.total_price,
            payment_method=PaymentMethod.CASH,  # Default para simplificar
            user_id=appointment.client_id,
        )
        self.db.add(transaction)
        await self.db.flush()

        rate = (
            await self.db.execute(select(Barber.commission_rate).where(Barber.id == appointment.barber_id))
        ).scalar_one()
        self.db.add(
            BarberCommission(
                barber_id=appointment.barber_id,
                transaction_id=transaction.id,
                amount=float(appointment.total_price) * (float(rate) / 100.0),
                is_paid=False,
            )
        )
