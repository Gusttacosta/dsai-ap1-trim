"""
Trim — Finance Service

Regras de negócio de PDV: checkout de agendamentos, produtos e geração de comissão.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.appointments.service import AppointmentService
from src.backend.modules.auth.models import User
from src.backend.modules.barbers.models import Barber
from src.backend.modules.finance.models import BarberCommission, PaymentMethod, Transaction, TransactionType
from src.backend.modules.finance.schemas import AppointmentCheckoutRequest, ProductCheckoutRequest
from src.backend.modules.loyalty.service import award_points
from src.backend.modules.products.models import MovementType
from src.backend.modules.products.service import ProductService
from src.backend.modules.products.schemas import InventoryMovementRequest
from src.backend.modules.subscriptions.models import SubscriptionStatus, UserSubscription


NOT_CONFIRMED_ERROR = "Só é possível cobrar um agendamento confirmado."
NOT_STARTED_ERROR = "Só é possível cobrar depois do início do agendamento."
NO_SUBSCRIPTION_ERROR = "O cliente não tem assinatura ativa do Trim Club."


class NotFound(LookupError):
    """Agendamento ou cliente inexistente (vira 404 na rota, #59)."""


class FinanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _clock(self) -> AppointmentService:
        # Mesmo "agora" e mesmo fuso da agenda (os testes fixam utc_now do módulo de agendamentos).
        return AppointmentService(self.db)

    async def _has_active_subscription(self, user_id: uuid.UUID) -> bool:
        today = self._clock().local_today()
        stmt = select(UserSubscription.id).where(
            UserSubscription.user_id == user_id,
            UserSubscription.status == SubscriptionStatus.ACTIVE,
            UserSubscription.start_date <= today,
            UserSubscription.end_date >= today,
        )
        return (await self.db.execute(stmt)).first() is not None

    async def checkout_appointment(self, appointment_id: uuid.UUID, data: AppointmentCheckoutRequest) -> Transaction:
        """Processa o pagamento de um agendamento e gera comissão."""
        # 1. Busca o agendamento
        stmt = select(Appointment).where(Appointment.id == appointment_id)
        appointment = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not appointment:
            raise NotFound("Agendamento não encontrado.")
            
        if appointment.status == AppointmentStatus.COMPLETED:
            raise ValueError("Este agendamento já foi finalizado e cobrado.")
        
        if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
            raise ValueError(f"Não é possível cobrar um agendamento com status {appointment.status.value}.")

        # Mesmas regras da conclusão pelo barbeiro (#26): só confirmado e já iniciado (#59).
        if appointment.status != AppointmentStatus.CONFIRMED:
            raise ValueError(NOT_CONFIRMED_ERROR)
        if appointment.start_datetime > self._clock().now():
            raise ValueError(NOT_STARTED_ERROR)

        # Crédito do Trim Club só para quem tem assinatura ativa hoje (#59).
        if data.payment_method == PaymentMethod.TRIM_CLUB_CREDIT and not await self._has_active_subscription(
            appointment.client_id
        ):
            raise ValueError(NO_SUBSCRIPTION_ERROR)

        # 2. Busca o barbeiro para ver a taxa de comissão
        stmt_barber = select(Barber).where(Barber.id == appointment.barber_id)
        barber = (await self.db.execute(stmt_barber)).scalar_one_or_none()

        # 3. Lógica Trim Club vs Pagamento normal
        amount = appointment.total_price
        commission_amount = amount * (barber.commission_rate / Decimal("100.0"))

        if data.payment_method == PaymentMethod.TRIM_CLUB_CREDIT:
            amount = Decimal("0.0")
            commission_amount = Decimal("0.0")

        # 4. Cria a Transação
        transaction = Transaction(
            type=TransactionType.APPOINTMENT,
            reference_id=appointment.id,
            amount=amount,
            payment_method=data.payment_method,
            user_id=appointment.client_id
        )
        self.db.add(transaction)
        await self.db.flush()
        # Pontos de fidelidade pelo valor pago; o crédito do Trim Club (0,00) não gera pontos (#13).
        await award_points(self.db, appointment.client_id, amount, "atendimento concluído")

        # 5. Cria a Comissão
        commission = BarberCommission(
            barber_id=barber.id,
            transaction_id=transaction.id,
            amount=commission_amount
        )
        self.db.add(commission)

        # 6. Atualiza o status do agendamento
        appointment.status = AppointmentStatus.COMPLETED

        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def checkout_product(self, data: ProductCheckoutRequest, admin_user_id: uuid.UUID) -> Transaction:
        """Vende um produto no balcão (baixa estoque + gera receita)."""
        product_service = ProductService(self.db)
        product = await product_service.get_product(data.product_id)
        
        if not product:
            raise ValueError("Produto não encontrado.")
        if not product.is_active:
            raise ValueError("Produto desativado não pode ser vendido.")
        # Antes, um cliente inexistente só estourava a FK depois da baixa do estoque (#59).
        if data.user_id is not None and await self.db.get(User, data.user_id) is None:
            raise NotFound("Cliente não encontrado.")

        amount = product.price * data.quantity
        if data.payment_method == PaymentMethod.TRIM_CLUB_CREDIT:
            # Assinantes podem ter descontos em produtos, mas na v1 eles não levam produtos de graça
            # O crédito do Trim Club é para serviços (ou conforme combinado).
            # Por segurança, vamos bloquear Trim Club para produtos por enquanto.
            raise ValueError("Produtos não podem ser pagos com créditos Trim Club nesta versão.")

        # 1. Baixa o estoque (ProductService faz a transação segura)
        movement = InventoryMovementRequest(
            quantity=-data.quantity,
            movement_type=MovementType.SALE,
            notes="Venda no balcão"
        )
        # Sem commit: a baixa do estoque e a transação entram juntas, ou nenhuma entra (#59).
        await product_service.register_movement(product.id, admin_user_id, movement, commit=False)
        
        # 2. Cria a Transação
        transaction = Transaction(
            type=TransactionType.PRODUCT_SALE,
            reference_id=product.id,
            amount=amount,
            payment_method=data.payment_method,
            user_id=data.user_id
        )
        self.db.add(transaction)
        # Compra com o cliente identificado também pontua (#13).
        await award_points(self.db, data.user_id, amount, "compra na loja")
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def list_transactions(self, start_date: date | None = None, end_date: date | None = None) -> list[Transaction]:
        """Lista as transações, com filtro opcional por dia no fuso da barbearia (#59)."""
        stmt = select(Transaction)
        clock = self._clock()
        if start_date:
            stmt = stmt.where(Transaction.created_at >= clock._local_to_utc(start_date, time.min))
        if end_date:
            stmt = stmt.where(Transaction.created_at < clock._local_to_utc(end_date + timedelta(days=1), time.min))
        stmt = stmt.order_by(Transaction.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def pending_commissions_by_barber(self) -> list[dict]:
        """(Admin) Comissões pendentes agrupadas por barbeiro, do maior valor para o menor (#59)."""
        stmt = (
            select(
                Barber.id,
                User.full_name,
                func.count(BarberCommission.id),
                func.coalesce(func.sum(BarberCommission.amount), 0),
            )
            .join(Barber, BarberCommission.barber_id == Barber.id)
            .join(User, Barber.user_id == User.id)
            .where(BarberCommission.is_paid.is_(False))
            .group_by(Barber.id, User.full_name)
            .order_by(func.sum(BarberCommission.amount).desc(), User.full_name)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {"barber_id": bid, "barber_name": name, "pending_count": n, "pending_amount": Decimal(total)}
            for bid, name, n, total in rows
        ]

    async def list_commissions_by_barber(self, barber_id: uuid.UUID, only_pending: bool = False) -> list[BarberCommission]:
        """Lista comissões de um barbeiro específico."""
        stmt = select(BarberCommission).where(BarberCommission.barber_id == barber_id)
        if only_pending:
            stmt = stmt.where(BarberCommission.is_paid == False)
        stmt = stmt.order_by(BarberCommission.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def pay_commissions(self, barber_id: uuid.UUID, commission_ids: list[uuid.UUID]) -> list[BarberCommission]:
        """Admin marca as comissões como pagas (acerto de contas)."""
        stmt = select(BarberCommission).where(
            BarberCommission.barber_id == barber_id,
            BarberCommission.id.in_(commission_ids),
            BarberCommission.is_paid == False
        )
        result = await self.db.execute(stmt)
        commissions = list(result.scalars().all())
        
        if not commissions:
            raise ValueError("Nenhuma comissão pendente encontrada com esses IDs.")
            
        now = datetime.now(timezone.utc)
        for comm in commissions:
            comm.is_paid = True
            comm.paid_at = now
            
        await self.db.commit()
        return commissions
