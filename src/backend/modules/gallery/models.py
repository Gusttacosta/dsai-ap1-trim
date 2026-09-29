"""
Trim — Gallery Models

Modelos SQLAlchemy para a galeria de imagens e portfólio.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base


# Tabela de associação N:N entre PortfolioImage e GalleryTag
portfolio_image_tags = Table(
    "portfolio_image_tags",
    Base.metadata,
    Column("image_id", UUID(as_uuid=True), ForeignKey("portfolio_images.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("gallery_tags.id", ondelete="CASCADE"), primary_key=True),
)


class GalleryTag(Base):
    """Tags visuais para filtro (ex: Fade, Afro, Navalhado)."""
    __tablename__ = "gallery_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PortfolioImage(Base):
    """Uma foto de corte no portfólio."""
    __tablename__ = "portfolio_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    image_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    barber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("barbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tags: Mapped[list["GalleryTag"]] = relationship(
        "GalleryTag", secondary=portfolio_image_tags, lazy="selectin"
    )
