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
async def seed_database(secret: str = "open", db: AsyncSession = Depends(get_db)):
    if secret != "trim2026":
        return {"error": "Acesso negado. Essa rota foi trancada."}
    
    from src.backend.modules.auth.security import get_password_hash
    from src.backend.modules.auth.models import UserRole
    from src.backend.modules.barbers.service import BarberService

    try:
        # Adiciona usuários admin e barbeiros
        user_q = await db.execute(select(User).where(User.email == "admin@trim.com"))
        admin = user_q.scalars().first()
        if not admin:
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
                apt2 = Appointment(
                    client_id=db_client.id,
                    barber_id=db_barber.id,
                    service_id=db_service.id,
                    scheduled_time=now - timedelta(days=1),
                    status=AppointmentStatus.COMPLETED
                )
                db.add_all([apt1, apt2])
                await db.flush()

        # Adiciona Despesas (Expenses)
        from src.backend.modules.expenses.models import Expense, ExpenseCategory, PaymentMethod
        exp_q = await db.execute(select(Expense))
        if not exp_q.scalars().first():
            db_admin = (await db.execute(select(User).where(User.email == "admin@trim.com"))).scalars().first()
            e1 = Expense(description="Conta de Luz", amount=350.00, category=ExpenseCategory.UTILITIES, payment_method=PaymentMethod.PIX, user_id=db_admin.id)
            e2 = Expense(description="Produtos de Limpeza", amount=120.00, category=ExpenseCategory.SUPPLIES, payment_method=PaymentMethod.CREDIT_CARD, user_id=db_admin.id)
            db.add_all([e1, e2])
            await db.flush()

        # Adiciona Galeria
        from src.backend.modules.gallery.models import GalleryItem, TagEnum
        gal_q = await db.execute(select(GalleryItem))
        if not gal_q.scalars().first():
            db_barber = (await db.execute(select(Barber))).scalars().first()
            g1 = GalleryItem(image_url="https://images.unsplash.com/photo-1599351431202-1e0f0137899a?auto=format&fit=crop&q=80&w=400", title="Fade Clássico", tag=TagEnum.FADE, barber_id=db_barber.id)
            g2 = GalleryItem(image_url="https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&q=80&w=400", title="Barba Lenhador", tag=TagEnum.BEARD, barber_id=db_barber.id)
            db.add_all([g1, g2])
            await db.flush()

        # Adiciona Fila Walk-in
        from src.backend.modules.walkin.models import WalkinQueue, WalkinStatus
        wq_q = await db.execute(select(WalkinQueue))
        if not wq_q.scalars().first():
            db_service = (await db.execute(select(Service))).scalars().first()
            w1 = WalkinQueue(customer_name="Marcos Antonio", service_id=db_service.id, status=WalkinStatus.WAITING)
            w2 = WalkinQueue(customer_name="Felipe Costa", service_id=db_service.id, status=WalkinStatus.IN_SERVICE)
            db.add_all([w1, w2])
            await db.flush()

        # Adiciona Pontos de Fidelidade
        from src.backend.modules.loyalty.models import LoyaltyPoints
        loy_q = await db.execute(select(LoyaltyPoints))
        if not loy_q.scalars().first():
            db_client = (await db.execute(select(User).where(User.email == "cliente@trim.com"))).scalars().first()
            l1 = LoyaltyPoints(user_id=db_client.id, points_balance=150, total_earned=150)
            db.add(l1)
            await db.flush()

        # Receitas Financeiras (Finance)
        from src.backend.modules.finance.models import Revenue, RevenueType
        rev_q = await db.execute(select(Revenue))
        if not rev_q.scalars().first():
            db_admin = (await db.execute(select(User).where(User.email == "admin@trim.com"))).scalars().first()
            r1 = Revenue(amount=75.0, type=RevenueType.SERVICE, payment_method=PaymentMethod.PIX, description="Corte + Barba do João", registered_by=db_admin.id)
            r2 = Revenue(amount=55.0, type=RevenueType.PRODUCT, payment_method=PaymentMethod.CREDIT_CARD, description="Pomada vendida balcão", registered_by=db_admin.id)
            r3 = Revenue(amount=120.0, type=RevenueType.SERVICE, payment_method=PaymentMethod.PIX, description="Platinado Lucas", registered_by=db_admin.id)
            db.add_all([r1, r2, r3])
            await db.flush()

        await db.commit()
        return {"message": "Banco populado MUDOU DE PATAMAR! Todas as tabelas têm dados!"}
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}
