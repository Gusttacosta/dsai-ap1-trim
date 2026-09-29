"""
Trim — Appointments Service

Lógica de negócio complexa de Agendamentos: motor de disponibilidade, 
prevenção de conflito e clonagem de dados financeiros.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.modules.appointments.models import Appointment, AppointmentItem, AppointmentStatus
from src.backend.modules.appointments.schemas import AppointmentCreateRequest
from src.backend.modules.barbers.models import WorkSchedule
from src.backend.modules.services.models import BarberServiceAssociation, Service


class AppointmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

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
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
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
        """Calcula slots disponíveis para uma duração específica em uma data."""
        schedule = await self._get_schedule_for_date(barber_id, target_date)
        
        if not schedule or not schedule.is_working:
            return []

        # Pega todos os agendamentos já marcados para este dia
        start_of_day = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        end_of_day = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
        
        stmt = select(Appointment.start_datetime, Appointment.end_datetime).where(
            Appointment.barber_id == barber_id,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
            Appointment.start_datetime >= start_of_day,
            Appointment.start_datetime <= end_of_day
        )
        result = await self.db.execute(stmt)
        booked_intervals = result.all()

        available_slots = []
        
        # Gerar slots de 30 em 30 minutos desde start_time até end_time
        # Simulando TZ UTC para os cálculos. Na vida real, aplicaria fuso local.
        current_dt = datetime.combine(target_date, schedule.start_time, tzinfo=timezone.utc)
        end_dt_limit = datetime.combine(target_date, schedule.end_time, tzinfo=timezone.utc)
        
        break_start_dt = None
        break_end_dt = None
        if schedule.break_start and schedule.break_end:
            break_start_dt = datetime.combine(target_date, schedule.break_start, tzinfo=timezone.utc)
            break_end_dt = datetime.combine(target_date, schedule.break_end, tzinfo=timezone.utc)

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
            
            if not is_break_conflict and not is_booked_conflict:
                available_slots.append(current_dt.strftime("%H:%M"))
            
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
        
        # Garante que start_datetime está no timezone correto (assumindo UTC)
        start_dt = data.start_datetime
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
            
        end_dt = start_dt + timedelta(minutes=total_duration)

        # 3. Verifica choque de horários na agenda do barbeiro
        if await self._check_conflict(data.barber_id, start_dt, end_dt):
            raise ValueError("Conflito de horário. O barbeiro já possui um agendamento nesse período.")

        # 4. Verifica se está dentro do horário de expediente
        schedule = await self._get_schedule_for_date(data.barber_id, start_dt.date())
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

    async def update_status(self, appointment_id: uuid.UUID, new_status: AppointmentStatus) -> Appointment | None:
        """Altera o status do agendamento (CANCELLED, COMPLETED, etc)."""
        stmt = select(Appointment).where(Appointment.id == appointment_id).options(selectinload(Appointment.items))
        result = await self.db.execute(stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            return None

        appointment.status = new_status
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
