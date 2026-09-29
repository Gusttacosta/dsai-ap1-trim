"""
Trim — Loyalty Service

Regras de negócio de acúmulo e resgate de pontos.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.modules.loyalty.models import LoyaltyWallet, Reward, RewardRedemption
from src.backend.modules.loyalty.schemas import RewardCreateRequest, RewardUpdateRequest


class LoyaltyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Carteira (Wallet) ────────────────────────────────────

    async def get_or_create_wallet(self, user_id: uuid.UUID) -> LoyaltyWallet:
        """Busca a carteira do usuário; se não existir, cria uma zerada."""
        stmt = select(LoyaltyWallet).where(LoyaltyWallet.user_id == user_id)
        wallet = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not wallet:
            wallet = LoyaltyWallet(user_id=user_id, balance=0, lifetime_points=0)
            self.db.add(wallet)
            await self.db.commit()
            await self.db.refresh(wallet)
            
        return wallet

    async def add_points(self, user_id: uuid.UUID, points: int) -> LoyaltyWallet:
        """Adiciona pontos à carteira de um usuário."""
        if points <= 0:
            raise ValueError("A quantidade de pontos deve ser maior que zero.")
            
        wallet = await self.get_or_create_wallet(user_id)
        
        wallet.balance += points
        wallet.lifetime_points += points
        
        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet


    # ── Catálogo (Rewards) ───────────────────────────────────

    async def create_reward(self, data: RewardCreateRequest) -> Reward:
        reward = Reward(**data.model_dump())
        self.db.add(reward)
        await self.db.commit()
        await self.db.refresh(reward)
        return reward

    async def update_reward(self, reward_id: uuid.UUID, data: RewardUpdateRequest) -> Reward | None:
        stmt = select(Reward).where(Reward.id == reward_id)
        reward = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not reward:
            return None
            
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(reward, key, value)
            
        await self.db.commit()
        await self.db.refresh(reward)
        return reward

    async def list_active_rewards(self) -> list[Reward]:
        stmt = select(Reward).where(Reward.is_active == True).order_by(Reward.points_cost.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    # ── Resgate (Redemption) ─────────────────────────────────

    async def redeem_reward(self, user_id: uuid.UUID, reward_id: uuid.UUID) -> RewardRedemption:
        """Troca pontos por um prêmio, debitando o saldo."""
        # 1. Busca o prêmio
        stmt_reward = select(Reward).where(Reward.id == reward_id, Reward.is_active == True)
        reward = (await self.db.execute(stmt_reward)).scalar_one_or_none()
        
        if not reward:
            raise ValueError("Prêmio não encontrado ou inativo.")
            
        # 2. Busca a carteira
        wallet = await self.get_or_create_wallet(user_id)
        
        # 3. Valida saldo
        if wallet.balance < reward.points_cost:
            raise ValueError(f"Saldo insuficiente. Você possui {wallet.balance} pts e o prêmio custa {reward.points_cost} pts.")
            
        # 4. Debita o saldo
        wallet.balance -= reward.points_cost
        
        # 5. Gera o histórico de resgate
        redemption = RewardRedemption(
            wallet_id=wallet.id,
            reward_id=reward.id,
            points_spent=reward.points_cost
        )
        
        self.db.add(redemption)
        await self.db.commit()
        
        # Recarrega para popular a relação .reward no schema de resposta
        stmt_refresh = select(RewardRedemption).where(RewardRedemption.id == redemption.id).options(selectinload(RewardRedemption.reward))
        result = await self.db.execute(stmt_refresh)
        return result.scalar_one()

    async def list_redemptions(self) -> list[RewardRedemption]:
        """(Admin) Lista histórico de resgates recentes."""
        stmt = select(RewardRedemption).options(selectinload(RewardRedemption.reward)).order_by(RewardRedemption.redeemed_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
