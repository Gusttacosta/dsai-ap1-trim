"""
Trim — Loyalty Models

Modelos SQLAlchemy para carteira de pontos, recompensas e resgates.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base


class LoyaltyWallet(Base):
    """Carteira de pontos do cliente."""
    __tablename__ = "loyalty_wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    balance: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    lifetime_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Reward(Base):
    """Catálogo de prêmios (Recompensas)."""
    __tablename__ = "rewards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    points_cost: Mapped[int] = mapped_column(
        Integer,
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


class RewardRedemption(Base):
    """Histórico de resgates (Quando a pessoa trocou pontos pelo prêmio)."""
    __tablename__ = "reward_redemptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loyalty_wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rewards.id", ondelete="RESTRICT"),
        nullable=False,
    )
    points_spent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    reward: Mapped["Reward"] = relationship("Reward")
    wallet: Mapped["LoyaltyWallet"] = relationship("LoyaltyWallet")
