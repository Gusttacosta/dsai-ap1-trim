"""
Trim — Services Service

Camada de serviço contendo as regras de negócio de Catálogo de Serviços
e suas associações com Barbeiros.
"""

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.modules.auth.models import User
from src.backend.modules.barbers.models import Barber
from src.backend.modules.barbers.schemas import BarberPublicResponse
from src.backend.modules.services.models import BarberServiceAssociation, Service
from src.backend.modules.services.schemas import ServiceCreateRequest, ServiceUpdateRequest, ServiceWithBarbersResponse


class CatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_service(self, data: ServiceCreateRequest) -> Service:
        """Cria um novo serviço no catálogo."""
        # Verifica se já existe um serviço com esse nome
        stmt = select(Service).where(Service.name == data.name)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ValueError(f"Já existe um serviço com o nome '{data.name}'")

        service = Service(**data.model_dump())
        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)
        return service

    async def update_service(self, service_id: uuid.UUID, data: ServiceUpdateRequest) -> Service | None:
        """Atualiza os dados de um serviço existente."""
        stmt = select(Service).where(Service.id == service_id)
        service = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not service:
            return None

        if data.name is not None and data.name != service.name:
            # Verifica se o novo nome já existe
            stmt_name = select(Service).where(Service.name == data.name)
            existing = (await self.db.execute(stmt_name)).scalar_one_or_none()
            if existing:
                raise ValueError(f"Já existe um serviço com o nome '{data.name}'")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(service, key, value)

        await self.db.commit()
        await self.db.refresh(service)
        return service

    async def deactivate_service(self, service_id: uuid.UUID) -> bool:
        """Faz soft delete (desativa) um serviço."""
        stmt = select(Service).where(Service.id == service_id)
        service = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not service:
            return False

        service.is_active = False
        await self.db.commit()
        return True

    async def list_active_services(self) -> list[Service]:
        """Lista apenas os serviços ativos para os clientes."""
        stmt = select(Service).where(Service.is_active == True).order_by(Service.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_service(self, service_id: uuid.UUID) -> Service | None:
        """Busca um serviço específico pelo ID."""
        stmt = select(Service).where(Service.id == service_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    # ── Associações com Barbeiros ────────────────────────

    async def link_barber_to_service(self, barber_id: uuid.UUID, service_id: uuid.UUID) -> bool:
        """Habilita um barbeiro a realizar um serviço específico."""
        assoc = BarberServiceAssociation(barber_id=barber_id, service_id=service_id)
        self.db.add(assoc)
        try:
            await self.db.commit()
            return True
        except IntegrityError:
            # Já existe a associação ou barber/service não existem
            await self.db.rollback()
            return False

    async def unlink_barber_from_service(self, barber_id: uuid.UUID, service_id: uuid.UUID) -> bool:
        """Desvincula um barbeiro de um serviço."""
        stmt = delete(BarberServiceAssociation).where(
            BarberServiceAssociation.barber_id == barber_id,
            BarberServiceAssociation.service_id == service_id
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_barbers_by_service(self, service_id: uuid.UUID) -> list[BarberPublicResponse]:
        """Retorna todos os barbeiros ativos habilitados a fazer o serviço."""
        stmt = (
            select(Barber, User)
            .join(BarberServiceAssociation, Barber.id == BarberServiceAssociation.barber_id)
            .join(User, Barber.user_id == User.id)
            .where(BarberServiceAssociation.service_id == service_id)
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

    async def get_services_by_barber(self, barber_id: uuid.UUID) -> list[Service]:
        """Retorna todos os serviços ativos que um barbeiro específico sabe fazer."""
        stmt = (
            select(Service)
            .join(BarberServiceAssociation, Service.id == BarberServiceAssociation.service_id)
            .where(BarberServiceAssociation.barber_id == barber_id)
            .where(Service.is_active == True)
            .order_by(Service.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
