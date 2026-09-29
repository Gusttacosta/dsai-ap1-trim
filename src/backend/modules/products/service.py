"""
Trim — Products Service

Regras de negócio do catálogo de produtos e da trilha de auditoria do estoque.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.backend.modules.products.models import InventoryMovement, MovementType, Product
from src.backend.modules.products.schemas import InventoryMovementRequest, ProductCreateRequest, ProductUpdateRequest


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Catálogo ─────────────────────────────────────────────

    async def create_product(self, data: ProductCreateRequest) -> Product:
        """Cria um novo produto (inicia com estoque zero)."""
        # Verifica se o SKU já existe (se fornecido)
        if data.sku:
            stmt = select(Product).where(Product.sku == data.sku)
            existing_sku = (await self.db.execute(stmt)).scalar_one_or_none()
            if existing_sku:
                raise ValueError(f"Já existe um produto com o SKU '{data.sku}'.")
        
        # Verifica se o nome já existe
        stmt = select(Product).where(Product.name == data.name)
        existing_name = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing_name:
            raise ValueError(f"Já existe um produto com o nome '{data.name}'.")

        product = Product(**data.model_dump())
        # O estoque padrão é 0, definido no Model.
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def update_product(self, product_id: uuid.UUID, data: ProductUpdateRequest) -> Product | None:
        """Atualiza os dados de um produto."""
        stmt = select(Product).where(Product.id == product_id)
        product = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not product:
            return None

        # Validações de unicidade se houver alteração
        if data.name is not None and data.name != product.name:
            stmt_name = select(Product).where(Product.name == data.name)
            if (await self.db.execute(stmt_name)).scalar_one_or_none():
                raise ValueError(f"Já existe um produto com o nome '{data.name}'.")
                
        if data.sku is not None and data.sku != product.sku:
            stmt_sku = select(Product).where(Product.sku == data.sku)
            if (await self.db.execute(stmt_sku)).scalar_one_or_none():
                raise ValueError(f"Já existe um produto com o SKU '{data.sku}'.")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(product, key, value)

        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def deactivate_product(self, product_id: uuid.UUID) -> bool:
        """Faz soft delete (desativa) um produto."""
        stmt = select(Product).where(Product.id == product_id)
        product = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not product:
            return False

        product.is_active = False
        await self.db.commit()
        return True

    async def list_public_products(self, show_out_of_stock: bool = False) -> list[Product]:
        """Lista os produtos para os clientes (apenas ativos, opcionalmente esconde sem estoque)."""
        stmt = select(Product).where(Product.is_active == True)
        
        if not show_out_of_stock:
            stmt = stmt.where(Product.stock_quantity > 0)
            
        stmt = stmt.order_by(Product.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_admin_products(self) -> list[Product]:
        """Lista todos os produtos para o Admin (ativos e inativos)."""
        stmt = select(Product).order_by(Product.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        """Busca um produto específico pelo ID."""
        stmt = select(Product).where(Product.id == product_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()


    # ── Estoque ──────────────────────────────────────────────

    async def register_movement(
        self, product_id: uuid.UUID, user_id: uuid.UUID, data: InventoryMovementRequest
    ) -> Product:
        """Registra a movimentação e atualiza o saldo atomicamente."""
        # Se for saída, a quantidade tem que ser negativa (ou vice-versa dependendo da interpretação).
        # Vamos assumir que a request já manda o sinal correto (+ ou -) no `data.quantity`.
        
        # 1. Recupera o produto (com lock para evitar race condition seria ideal em produção de alta concorrência: with_for_update())
        stmt = select(Product).where(Product.id == product_id).with_for_update()
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            raise ValueError("Produto não encontrado.")

        # 2. Verifica se a movimentação resultará em saldo negativo
        new_quantity = product.stock_quantity + data.quantity
        if new_quantity < 0:
            raise ValueError(
                f"Estoque insuficiente. Tentativa de remover {-data.quantity}, mas só existem {product.stock_quantity} unidades."
            )

        # 3. Atualiza saldo no produto
        product.stock_quantity = new_quantity

        # 4. Registra histórico (trilha de auditoria)
        movement = InventoryMovement(
            product_id=product.id,
            user_id=user_id,
            quantity=data.quantity,
            movement_type=data.movement_type,
            notes=data.notes
        )
        self.db.add(movement)
        
        # O commit garantirá o CheckConstraint `chk_stock_non_negative` do DB
        try:
            await self.db.commit()
            await self.db.refresh(product)
            return product
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Erro de integridade de estoque (estoque negativo detectado pelo banco).")

    async def get_product_movements(self, product_id: uuid.UUID) -> list[InventoryMovement]:
        """Retorna o histórico de movimentação de um produto específico."""
        stmt = select(InventoryMovement).where(
            InventoryMovement.product_id == product_id
        ).order_by(InventoryMovement.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
