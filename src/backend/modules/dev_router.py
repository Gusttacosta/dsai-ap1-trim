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
    try:
        # Adiciona usuários admin e barbeiros
        user_q = await db.execute(select(User).where(User.email == "admin@trim.com"))
        admin = user_q.scalars().first()
        if not admin:
            from src.backend.modules.auth.security import get_password_hash
            from src.backend.modules.auth.models import UserRole
            admin = User(
                email="admin@trim.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Gustavo Admin",
                role=UserRole.ADMIN
            )
            db.add(admin)
            await db.flush()

        # Cria perfil de barbeiro se não existir
        barber_q = await db.execute(select(Barber).where(Barber.user_id == admin.id))
        if not barber_q.scalars().first():
            from src.backend.modules.barbers.service import BarberService
            b_service = BarberService(db)
            barber = Barber(
                user_id=admin.id,
                bio="Especialista Trim",
                commission_rate=50.0
            )
            db.add(barber)
            await db.flush()
            await b_service._create_default_schedules(barber.id)
        
        await db.commit()

        # Adiciona Serviços
        srv_q = await db.execute(select(Service))
        if not srv_q.scalars().first():
            s1 = Service(name="Corte Máquina", description="Corte simples na máquina", duration_minutes=30, price=40.0)
            s2 = Service(name="Corte + Barba", description="Pacote completo", duration_minutes=60, price=75.0)
            s3 = Service(name="Platinado", description="Descoloração total", duration_minutes=120, price=120.0)
            s4 = Service(name="Pezinho e Sobrancelha", description="Acabamento", duration_minutes=20, price=25.0)
            db.add_all([s1, s2, s3, s4])
            await db.flush()

        # Adiciona Barbeiros Extras
        barber2_q = await db.execute(select(User).where(User.email == "carlos@trim.com"))
        if not barber2_q.scalars().first():
            barber_user = User(
                email="carlos@trim.com",
                hashed_password=get_password_hash("barber123"),
                full_name="Carlos Santos",
                role=UserRole.BARBER
            )
            db.add(barber_user)
            await db.flush()
            barber2 = Barber(user_id=barber_user.id, bio="Navalha Clássica", commission_rate=50.0)
            db.add(barber2)
            await db.flush()
            await b_service._create_default_schedules(barber2.id)

        # Adiciona Clientes
        client_q = await db.execute(select(User).where(User.email == "cliente@trim.com"))
        client = client_q.scalars().first()
        if not client:
            client = User(
                email="cliente@trim.com",
                hashed_password=get_password_hash("cliente123"),
                full_name="João Silva (Cliente)",
                role=UserRole.CLIENT
            )
            db.add(client)
            await db.flush()

        # Adiciona Produtos
        prod_q = await db.execute(select(Product))
        if not prod_q.scalars().first():
            p1 = Product(name="Pomada Efeito Matte Trim", description="Pomada", price=55.0, stock_quantity=42, is_active=True)
            p2 = Product(name="Óleo para Barba Premium", description="Óleo", price=89.9, stock_quantity=15, is_active=True)
            p3 = Product(name="Balm Refrescante", description="Pós barba", price=45.0, stock_quantity=8, is_active=True)
            db.add_all([p1, p2, p3])
            await db.flush()

        # Adiciona Agendamentos (Appointments)
        from src.backend.modules.appointments.models import Appointment, AppointmentStatus
        from datetime import datetime, timedelta
        
        apt_q = await db.execute(select(Appointment))
        if not apt_q.scalars().first():
            # Get the references we just created/queried
            db_client = (await db.execute(select(User).where(User.email == "cliente@trim.com"))).scalars().first()
            db_barber = (await db.execute(select(Barber))).scalars().first()
            db_service = (await db.execute(select(Service))).scalars().first()

            if db_client and db_barber and db_service:
                now = datetime.now()
                apt1 = Appointment(
                    client_id=db_client.id,
                    barber_id=db_barber.id,
                    service_id=db_service.id,
                    scheduled_time=now + timedelta(hours=2),
                    status=AppointmentStatus.SCHEDULED
                )
                db.add(apt1)
                await db.flush()

        await db.commit()
        return {"message": "Banco populado com SUCESSO! Muito mais dados adicionados!"}
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}
