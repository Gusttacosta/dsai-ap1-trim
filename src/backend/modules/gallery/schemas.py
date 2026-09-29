"""
Trim — Gallery Schemas

Schemas Pydantic para validação das imagens e tags do portfólio.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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
