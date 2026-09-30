from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.backend.database import get_db
from src.backend.modules.auth.models import User
from src.backend.modules.barbers.models import Barber
from src.backend.modules.services.models import Service
from src.backend.modules.products.models import Product

router = APIRouter()

@router.post("/seed", summary="Popula o banco com dados iniciais (Dev/Demonstração)")
async def seed_database(db: AsyncSession = Depends(get_db)):
    # Adiciona usuários admin e barbeiros
    user_q = await db.execute(select(User).where(User.email == "admin@trim.com"))
    if not user_q.scalars().first():
        from src.backend.modules.auth.security import get_password_hash
        admin = User(
            email="admin@trim.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Gustavo Admin",
            role="ADMIN"
        )
        db.add(admin)
        await db.commit()

    # Adiciona Serviços
    srv_q = await db.execute(select(Service))
    if not srv_q.scalars().first():
        s1 = Service(name="Corte Máquina", description="Corte simples na máquina", duration_minutes=30, price=40.0)
        s2 = Service(name="Corte + Barba", description="Pacote completo", duration_minutes=60, price=75.0)
        s3 = Service(name="Platinado", description="Descoloração total", duration_minutes=120, price=120.0)
        db.add_all([s1, s2, s3])
        await db.commit()

    # Adiciona Produtos
    prod_q = await db.execute(select(Product))
    if not prod_q.scalars().first():
        p1 = Product(name="Pomada Efeito Matte Trim", description="Pomada", price=55.0, stock_quantity=42, is_active=True)
        p2 = Product(name="Óleo para Barba Premium", description="Óleo", price=89.9, stock_quantity=15, is_active=True)
        db.add_all([p1, p2])
        await db.commit()

    return {"message": "Banco populado com sucesso!"}
