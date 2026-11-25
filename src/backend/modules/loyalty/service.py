"""
Trim — Loyalty Service

Regras de negócio de acúmulo e resgate de pontos.
SPEC/2026-11-25-fidelidade-correcoes.md (#73): usuário desconhecido, nomes de prêmio, trava no
resgate e operações do admin.
"""

import uuid
from decimal import ROUND_FLOOR, Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.modules.auth.models import User
from src.backend.modules.loyalty.models import LoyaltyWallet, Reward, RewardRedemption
from src.backend.modules.loyalty.schemas import RewardCreateRequest, RewardUpdateRequest
from src.backend.modules.notifications.models import NotificationType
from src.backend.modules.notifications.service import notify


class NotFound(LookupError):
    """Usuário ou prêmio inexistente (vira 404 na rota)."""


def points_for(amount) -> int:
    """Regra de pontuação (#13): 1 ponto por real pago, sem centavos."""
    return int(Decimal(str(amount or 0)).to_integral_value(rounding=ROUND_FLOOR))


async def award_points(db: AsyncSession, user_id: uuid.UUID | None, amount, reason: str) -> int:
    """Credita os pontos de um pagamento, sem commit: entram junto com a cobrança (#13).

    Pagamento de valor zero (crédito do Trim Club), venda sem cliente e conta desativada (inclusive
    o usuário Visitante, #21) não geram pontos. Devolve quantos pontos entraram."""
    points = points_for(amount)
    if user_id is None or points <= 0:
        return 0
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return 0

    stmt = select(LoyaltyWallet).where(LoyaltyWallet.user_id == user_id).with_for_update()
    wallet = (await db.execute(stmt)).scalar_one_or_none()
    if wallet is None:
        wallet = LoyaltyWallet(user_id=user_id, balance=0, lifetime_points=0)
        db.add(wallet)
    wallet.balance += points
    wallet.lifetime_points += points
    await notify(
        db, user_id, "Você ganhou pontos",
        f"+{points} pts por {reason}. Saldo: {wallet.balance} pts.", NotificationType.LOYALTY_UPDATE,
    )
    await db.flush()
    return points


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
            try:
                await self.db.commit()
            except IntegrityError:
                # Outro pedido criou a carteira ao mesmo tempo (user_id é único).
                await self.db.rollback()
                return (await self.db.execute(stmt)).scalar_one()
            await self.db.refresh(wallet)

        return wallet

    async def _locked_wallet(self, user_id: uuid.UUID) -> LoyaltyWallet:
        """Carteira travada (`SELECT ... FOR UPDATE`) até o commit: dois resgates ou estornos
        simultâneos esperam um pelo outro em vez de debitarem o mesmo saldo (#73)."""
        await self.get_or_create_wallet(user_id)
        stmt = (
            select(LoyaltyWallet)
            .where(LoyaltyWallet.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def _require_user(self, user_id: uuid.UUID) -> None:
        # Sem isso, a carteira estourava a FK e a rota respondia 500 (#73).
        if await self.db.get(User, user_id) is None:
            raise NotFound("Usuário não encontrado.")

    async def add_points(self, user_id: uuid.UUID, points: int) -> LoyaltyWallet:
        """Adiciona pontos à carteira de um usuário."""
        if points <= 0:
            raise ValueError("A quantidade de pontos deve ser maior que zero.")
        await self._require_user(user_id)

        wallet = await self._locked_wallet(user_id)
        wallet.balance += points
        wallet.lifetime_points += points
        await notify(
            self.db, user_id, "Você ganhou pontos",
            f"+{points} pts da barbearia. Saldo: {wallet.balance} pts.", NotificationType.LOYALTY_UPDATE,
        )

        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet

    async def remove_points(self, user_id: uuid.UUID, points: int) -> LoyaltyWallet:
        """(Admin) Estorna ou corrige pontos. Não mexe no total acumulado (#73)."""
        if points <= 0:
            raise ValueError("A quantidade de pontos deve ser maior que zero.")
        await self._require_user(user_id)

        wallet = await self._locked_wallet(user_id)
        if wallet.balance < points:
            balance = wallet.balance  # o rollback expira a carteira: ler o saldo antes
            await self.db.rollback()
            raise ValueError(f"Saldo insuficiente para retirar {points} pts. O cliente possui {balance} pts.")
        wallet.balance -= points

        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet

    async def list_wallets(self) -> list[dict]:
        """(Admin) Carteiras com o cliente, do maior saldo para o menor (#73)."""
        stmt = (
            select(LoyaltyWallet, User.full_name, User.email)
            .join(User, LoyaltyWallet.user_id == User.id)
            .order_by(LoyaltyWallet.balance.desc(), User.full_name)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "id": w.id, "user_id": w.user_id, "balance": w.balance, "lifetime_points": w.lifetime_points,
                "updated_at": w.updated_at, "full_name": name, "email": email,
            }
            for w, name, email in rows
        ]


    # ── Catálogo (Rewards) ───────────────────────────────────

    async def _check_unique_name(self, name: str, ignore_id: uuid.UUID | None = None) -> None:
        """Dois prêmios não podem ter o mesmo nome, sem diferenciar maiúsculas (#73)."""
        stmt = select(Reward.id).where(func.lower(Reward.name) == name.lower())
        if ignore_id is not None:
            stmt = stmt.where(Reward.id != ignore_id)
        if (await self.db.execute(stmt)).first():
            raise ValueError(f"Já existe um prêmio chamado '{name}'.")

    async def create_reward(self, data: RewardCreateRequest) -> Reward:
        await self._check_unique_name(data.name)
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

        changes = data.model_dump(exclude_unset=True)
        if "name" in changes:
            await self._check_unique_name(changes["name"], ignore_id=reward_id)
        for key, value in changes.items():
            setattr(reward, key, value)

        await self.db.commit()
        await self.db.refresh(reward)
        return reward

    async def list_active_rewards(self) -> list[Reward]:
        stmt = select(Reward).where(Reward.is_active.is_(True)).order_by(Reward.points_cost.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    # ── Resgate (Redemption) ─────────────────────────────────

    def _redemptions(self):
        return select(RewardRedemption).options(
            selectinload(RewardRedemption.reward), selectinload(RewardRedemption.wallet)
        )

    async def redeem_reward(self, user_id: uuid.UUID, reward_id: uuid.UUID) -> RewardRedemption:
        """Troca pontos por um prêmio, debitando o saldo."""
        # 1. Busca o prêmio
        stmt_reward = select(Reward).where(Reward.id == reward_id, Reward.is_active.is_(True))
        reward = (await self.db.execute(stmt_reward)).scalar_one_or_none()

        if not reward:
            raise ValueError("Prêmio não encontrado ou inativo.")

        # 2. Busca a carteira, travada até o commit (#73)
        wallet = await self._locked_wallet(user_id)

        # 3. Valida saldo
        if wallet.balance < reward.points_cost:
            balance, cost = wallet.balance, reward.points_cost  # o rollback expira os objetos
            await self.db.rollback()
            raise ValueError(f"Saldo insuficiente. Você possui {balance} pts e o prêmio custa {cost} pts.")

        # 4. Debita o saldo
        wallet.balance -= reward.points_cost

        # 5. Gera o histórico de resgate
        redemption = RewardRedemption(
            wallet_id=wallet.id,
            reward_id=reward.id,
            points_spent=reward.points_cost
        )

        self.db.add(redemption)
        await notify(
            self.db, user_id, "Resgate confirmado",
            f"Você trocou {reward.points_cost} pts por {reward.name}. Saldo: {wallet.balance} pts.",
            NotificationType.LOYALTY_UPDATE,
        )
        await self.db.commit()

        # Recarrega para popular as relações do schema de resposta
        result = await self.db.execute(self._redemptions().where(RewardRedemption.id == redemption.id))
        return result.scalar_one()

    async def list_redemptions(self) -> list[RewardRedemption]:
        """(Admin) Lista histórico de resgates recentes."""
        stmt = self._redemptions().order_by(RewardRedemption.redeemed_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
