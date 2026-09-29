"""
Trim — Finance Service

Regras de negócio de PDV: checkout de agendamentos, produtos e geração de comissão.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.modules.appointments.models import Appointment, AppointmentStatus
from src.backend.modules.barbers.models import Barber
from src.backend.modules.finance.models import BarberCommission, PaymentMethod, Transaction, TransactionType
from src.backend.modules.finance.schemas import AppointmentCheckoutRequest, ProductCheckoutRequest
from src.backend.modules.products.models import MovementType
from src.backend.modules.products.service import ProductService
from src.backend.modules.products.schemas import InventoryMovementRequest


class FinanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def checkout_appointment(self, appointment_id: uuid.UUID, data: AppointmentCheckoutRequest) -> Transaction:
        """Processa o pagamento de um agendamento e gera comissão."""
        # 1. Busca o agendamento
        stmt = select(Appointment).where(Appointment.id == appointment_id)
        appointment = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not appointment:
            raise ValueError("Agendamento não encontrado.")
            
        if appointment.status == AppointmentStatus.COMPLETED:
            raise ValueError("Este agendamento já foi finalizado e cobrado.")
        
        if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
            raise ValueError(f"Não é possível cobrar um agendamento com status {appointment.status.value}.")

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
        await product_service.register_movement(product.id, admin_user_id, movement)
        
        # O método acima já dá commit, então continuamos numa nova "fase"
        
        # 2. Cria a Transação
        transaction = Transaction(
            type=TransactionType.PRODUCT_SALE,
            reference_id=product.id,
            amount=amount,
            payment_method=data.payment_method,
            user_id=data.user_id
        )
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def list_transactions(self) -> list[Transaction]:
        """Lista todas as transações."""
        stmt = select(Transaction).order_by(Transaction.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
