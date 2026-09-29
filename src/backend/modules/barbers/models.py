"""
Trim — Barbers Models

Modelos SQLAlchemy para gestão da equipe de barbeiros.
"""

import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base


class Barber(Base):
    """
    Perfil estendido para usuários que são barbeiros.
    Relação 1:1 com a tabela de Users.
    """
    __tablename__ = "barbers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    instagram_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    commission_rate: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=50.0,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relacionamento com a escala de trabalho
    schedules: Mapped[list["WorkSchedule"]] = relationship(
        "WorkSchedule", back_populates="barber", cascade="all, delete-orphan"
    )


class WorkSchedule(Base):
    """
    Escala de trabalho de um barbeiro.
    Um registro para cada dia da semana (0 = Domingo, 6 = Sábado).
    """
    __tablename__ = "work_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    barber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("barbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    break_start: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )
    break_end: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )
    is_working: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    barber: Mapped["Barber"] = relationship("Barber", back_populates="schedules")
