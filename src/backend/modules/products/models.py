"""
Trim — Products Models

Modelos SQLAlchemy para catálogo de produtos e controle de estoque.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base


class MovementType(str, enum.Enum):
    SALE = "sale"
    RESTOCK = "restock"
    LOSS = "loss"
    ADJUSTMENT = "adjustment"


class Product(Base):
    """
    Catálogo de produtos físicos (pomadas, óleos, etc).
    """
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    sku: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )
    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    cost_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
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

    __table_args__ = (
        # Garante a nível de banco que o estoque não fique negativo
        CheckConstraint("stock_quantity >= 0", name="chk_stock_non_negative"),
    )

    # Relacionamento com histórico
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement", back_populates="product", cascade="all, delete-orphan"
    )


class InventoryMovement(Base):
    """
    Trilha de auditoria das movimentações de estoque.
    Toda entrada ou saída gera um registro aqui.
    """
    __tablename__ = "inventory_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        # quantity pode ser negativa (saída) ou positiva (entrada)
    )
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, name="movement_type", create_constraint=True),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    product: Mapped["Product"] = relationship("Product", back_populates="movements")
