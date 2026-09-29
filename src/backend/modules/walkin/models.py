"""
Trim — Walk-in Models

Modelos SQLAlchemy para a fila de espera da barbearia.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base


class WalkInStatus(str, enum.Enum):
    WAITING = "waiting"
    ATTENDING = "attending"
    CANCELLED = "cancelled"


class WalkInQueue(Base):
    """Registro de um cliente aguardando na fila de espera."""
    __tablename__ = "walk_in_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_barber_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("barbers.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[WalkInStatus] = mapped_column(
        Enum(WalkInStatus, name="walkin_status", create_constraint=True),
        nullable=False,
        default=WalkInStatus.WAITING,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
