"""
Trim — Barbers Service

Regras de negócio para o módulo de barbeiros.
"""

import uuid
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.modules.auth.models import User, UserRole
from src.backend.modules.barbers.models import Barber, WorkSchedule
from src.backend.modules.barbers.schemas import BarberCreateRequest, BarberPublicResponse


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

    async def update_schedule(self, barber_id: uuid.UUID, schedule_id: uuid.UUID, data: dict) -> WorkSchedule | None:
        """Atualiza um dia específico na escala."""
        stmt = select(WorkSchedule).where(
            WorkSchedule.id == schedule_id,
            WorkSchedule.barber_id == barber_id
        )
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            return None

        for key, value in data.items():
            setattr(schedule, key, value)

        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule
