"""
Trim — Barbers Service

Regras de negócio para o módulo de barbeiros.
"""

import uuid
from datetime import datetime, time, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber, WorkSchedule
from src.backend.modules.barbers.schemas import (
    DAY_CHANGED,
    SEVEN_DAYS,
    BarberAdminResponse,
    BarberCreateRequest,
    BarberDetailResponse,
    BarberPublicResponse,
    BarberServiceSummary,
    BarberUpdateAdminRequest,
    WorkScheduleDay,
    WorkScheduleUpdate,
    check_work_day,
)
from src.backend.modules.services.models import BarberServiceAssociation, Service

# Agendamentos que ainda vão acontecer e impedem a desativação (SPEC/2026-11-23-barbeiros-admin-escala.md).
OPEN_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)


class InvalidSchedule(ValueError):
    """Escala que quebra uma regra: o router responde 422 com a mensagem."""


def admin_view(barber: Barber, user: User) -> BarberAdminResponse:
    return BarberAdminResponse(
        id=barber.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        avatar_url=user.avatar_url,
        bio=barber.bio,
        instagram_url=barber.instagram_url,
        commission_rate=barber.commission_rate,
        is_active=barber.is_active,
        user_is_active=user.is_active,
        created_at=barber.created_at,
        updated_at=barber.updated_at,
    )


class BarberService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _create_default_schedules(self, barber_id: uuid.UUID) -> list[WorkSchedule]:
        """Cria a escala de segunda a sábado (9 às 18, almoço 12 às 13). Domingo é folga."""
        schedules = []
        for day in range(7):
            is_working = day != 0  # Domingo (0) não trabalha
            schedule = WorkSchedule(
                barber_id=barber_id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(18, 0),
                break_start=time(12, 0) if is_working else None,
                break_end=time(13, 0) if is_working else None,
                is_working=is_working,
            )
            schedules.append(schedule)
            self.db.add(schedule)
        return schedules

    async def create_barber(self, data: BarberCreateRequest) -> Barber:
        """Promove um usuário existente a barbeiro e gera sua escala."""
        # Verifica se o User existe
        stmt_user = select(User).where(User.id == data.user_id)
        result_user = await self.db.execute(stmt_user)
        user = result_user.scalar_one_or_none()
        
        if not user:
            raise ValueError("Usuário não encontrado.")

        # Verifica se já é barbeiro
        stmt_barber = select(Barber).where(Barber.user_id == data.user_id)
        result_barber = await self.db.execute(stmt_barber)
        if result_barber.scalar_one_or_none():
            raise ValueError("Usuário já possui perfil de barbeiro.")

        # Atualiza o role do usuário para BARBER, caso não seja ADMIN
        if user.role == UserRole.CLIENT:
            user.role = UserRole.BARBER

        # Cria o perfil Barber
        barber = Barber(
            user_id=data.user_id,
            bio=data.bio,
            instagram_url=str(data.instagram_url) if data.instagram_url else None,
            commission_rate=data.commission_rate,
        )
        self.db.add(barber)
        await self.db.flush()

        # Cria a escala padrão
        await self._create_default_schedules(barber.id)
        
        await self.db.commit()
        await self.db.refresh(barber)
        return barber

    async def list_active_barbers(self) -> list[BarberPublicResponse]:
        """Retorna todos os barbeiros ativos mesclados com dados do usuário."""
        # Fazemos um join entre Barber e User
        stmt = (
            select(Barber, User)
            .join(User, Barber.user_id == User.id)
            .where(Barber.is_active == True)
            .where(User.is_active == True)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        responses = []
        for barber, user in rows:
            responses.append(
                BarberPublicResponse(
                    id=barber.id,
                    user_id=user.id,
                    full_name=user.full_name,
                    avatar_url=user.avatar_url,
                    bio=barber.bio,
                    instagram_url=barber.instagram_url,
                )
            )
        return responses

    async def get_barber_by_id(self, barber_id: uuid.UUID) -> tuple[Barber, User] | None:
        """Busca um barbeiro pelo ID e o respectivo usuário."""
        stmt = (
            select(Barber, User)
            .join(User, Barber.user_id == User.id)
            .where(Barber.id == barber_id)
        )
        result = await self.db.execute(stmt)
        return result.first()

    async def get_barber_by_user_id(self, user_id: uuid.UUID) -> Barber | None:
        """Busca o perfil Barber associado a um User."""
        stmt = select(Barber).where(Barber.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_schedules(self, barber_id: uuid.UUID) -> list[WorkSchedule]:
        """Retorna a escala de trabalho do barbeiro (ordenada por dia)."""
        stmt = select(WorkSchedule).where(WorkSchedule.barber_id == barber_id).order_by(WorkSchedule.day_of_week)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_schedule(
        self, barber_id: uuid.UUID, schedule_id: uuid.UUID, data: WorkScheduleUpdate
    ) -> WorkSchedule | None:
        """Altera só os campos enviados de um dia e confere as regras no resultado."""
        stmt = select(WorkSchedule).where(
            WorkSchedule.id == schedule_id,
            WorkSchedule.barber_id == barber_id
        )
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            return None

        changes = data.model_dump(exclude_unset=True)
        if changes.pop("day_of_week", schedule.day_of_week) != schedule.day_of_week:
            raise InvalidSchedule(DAY_CHANGED)
        merged = {
            field: changes.get(field, getattr(schedule, field))
            for field in ("start_time", "end_time", "break_start", "break_end")
        }
        try:
            check_work_day(merged["start_time"], merged["end_time"], merged["break_start"], merged["break_end"])
        except ValueError as e:
            raise InvalidSchedule(str(e)) from e

        for key, value in changes.items():
            setattr(schedule, key, value)

        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def replace_week(self, barber_id: uuid.UUID, days: list[WorkScheduleDay]) -> list[WorkSchedule] | None:
        """Grava os 7 dias de uma vez (cada dia já validado). None se o barbeiro não existe."""
        if sorted(day.day_of_week for day in days) != list(range(7)):
            raise InvalidSchedule(SEVEN_DAYS)
        if await self.db.get(Barber, barber_id) is None:
            return None

        stored = {s.day_of_week: s for s in await self.get_schedules(barber_id)}
        for day in days:
            schedule = stored.get(day.day_of_week)
            if schedule is None:
                schedule = WorkSchedule(barber_id=barber_id, day_of_week=day.day_of_week)
                self.db.add(schedule)
            for key, value in day.model_dump(exclude={"day_of_week"}).items():
                setattr(schedule, key, value)

        await self.db.commit()
        return await self.get_schedules(barber_id)

    # ── Admin ────────────────────────────────────────────

    async def list_all_barbers(self) -> list[BarberAdminResponse]:
        """Todos os barbeiros, ativos e desativados, em ordem alfabética do nome."""
        stmt = (
            select(Barber, User)
            .join(User, Barber.user_id == User.id)
            .order_by(func.lower(User.full_name), User.full_name)
        )
        rows = (await self.db.execute(stmt)).all()
        return [admin_view(barber, user) for barber, user in rows]

    async def count_open_appointments(self, barber_id: uuid.UUID) -> int:
        """Agendamentos pendentes ou confirmados do barbeiro que ainda não começaram."""
        stmt = select(func.count()).select_from(Appointment).where(
            Appointment.barber_id == barber_id,
            Appointment.status.in_(OPEN_STATUSES),
            Appointment.start_datetime > datetime.now(timezone.utc),
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def update_barber(self, barber_id: uuid.UUID, data: BarberUpdateAdminRequest) -> BarberAdminResponse | None:
        """Alteração parcial pelo admin. A desativação é recusada com agendamentos futuros."""
        result = await self.get_barber_by_id(barber_id)
        if not result:
            return None
        barber, user = result

        changes = data.model_dump(exclude_unset=True)
        if changes.get("is_active") is False and barber.is_active:
            pending = await self.count_open_appointments(barber_id)
            if pending:
                raise ValueError(
                    f"O barbeiro tem {pending} agendamento(s) futuro(s). Cancele ou remaneje antes de desativá-lo."
                )
        if changes.get("instagram_url") is not None:
            changes["instagram_url"] = str(data.instagram_url)

        for key, value in changes.items():
            setattr(barber, key, value)
        await self.db.commit()
        await self.db.refresh(barber)
        return admin_view(barber, user)

    # ── Detalhes públicos e perfil do próprio barbeiro ───

    async def get_active_barber_detail(self, barber_id: uuid.UUID) -> BarberDetailResponse | None:
        """Detalhes públicos com os serviços ativos vinculados. None se não existe ou está inativo."""
        result = await self.get_barber_by_id(barber_id)
        if not result:
            return None
        barber, user = result
        if not barber.is_active or not user.is_active:
            return None

        stmt = (
            select(Service)
            .join(BarberServiceAssociation, Service.id == BarberServiceAssociation.service_id)
            .where(BarberServiceAssociation.barber_id == barber_id, Service.is_active.is_(True))
            .order_by(func.lower(Service.name), Service.name)
        )
        services = (await self.db.execute(stmt)).scalars().all()
        return BarberDetailResponse(
            id=barber.id,
            user_id=user.id,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            bio=barber.bio,
            instagram_url=barber.instagram_url,
            services=[BarberServiceSummary.model_validate(s) for s in services],
        )

    async def update_own_profile(self, barber: Barber, changes: dict) -> Barber:
        """Bio e Instagram do próprio barbeiro: só os campos enviados, e null apaga."""
        for key, value in changes.items():
            if key == "instagram_url" and value is not None:
                value = str(value)
            setattr(barber, key, value)
        await self.db.commit()
        await self.db.refresh(barber)
        return barber
