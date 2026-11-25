"""
Trim — Gallery Schemas

Schemas Pydantic para validação das imagens e tags do portfólio.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

IMAGE_URL_MAX = 1000


class GalleryTagCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # Nome vazio era aceito (#71).
    name: str = Field(..., min_length=1, max_length=50)


class GalleryTagUpdateRequest(GalleryTagCreateRequest):
    """Renomear uma tag (#71)."""


class PortfolioImageRejectRequest(BaseModel):
    """Recusa de uma foto pendente: o motivo vai para o barbeiro como notificação (#71)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str = Field(..., min_length=1, max_length=500)


class GalleryTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str


class PortfolioImageCreateRequest(BaseModel):
    image_url: HttpUrl
    service_id: uuid.UUID | None = None
    description: str | None = Field(None, max_length=500)
    tag_ids: list[uuid.UUID] = Field(default_factory=list)
    # Só o admin escolhe o barbeiro da foto; o barbeiro só envia para o próprio portfólio (#71).
    barber_id: uuid.UUID | None = None

    @field_validator("image_url")
    @classmethod
    def fits_the_column(cls, value: HttpUrl) -> HttpUrl:
        # A coluna é String(1000), e o HttpUrl aceita até 2.083 caracteres (#71).
        if len(str(value)) > IMAGE_URL_MAX:
            raise ValueError(f"A URL da imagem pode ter no máximo {IMAGE_URL_MAX} caracteres.")
        return value


class PortfolioImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    image_url: str
    barber_id: uuid.UUID
    service_id: uuid.UUID | None
    description: str | None
    is_approved: bool
    created_at: datetime
    
    tags: list[GalleryTagResponse]
