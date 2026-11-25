"""
Trim — Gallery Schemas

Schemas Pydantic para validação das imagens e tags do portfólio.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

IMAGE_URL_MAX = 1000


class GalleryTagCreateRequest(BaseModel):
    name: str = Field(..., max_length=50)


class GalleryTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str


class PortfolioImageCreateRequest(BaseModel):
    image_url: HttpUrl
    service_id: uuid.UUID | None = None
    description: str | None = Field(None, max_length=500)
    tag_ids: list[uuid.UUID] = Field(default_factory=list)

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
