import type { Redemption, Reward, Wallet } from '../hooks/useLoyaltyAdmin';

// Prêmios, carteiras e resgates como a API os devolve, para os testes da fidelidade no painel
// (SPEC/2026-11-26-painel-fidelidade.md).

export function makeReward(id: string, extra: Partial<Reward> = {}): Reward {
  return {
    id,
    name: `Prêmio ${id}`,
    description: null,
    points_cost: 100,
    is_active: true,
    created_at: '2026-11-20T12:00:00Z',
    ...extra,
  };
}

export const POMADA = makeReward('pomada', { name: 'Pomada', points_cost: 120 });
export const CORTE = makeReward('corte', { name: 'Corte grátis', description: 'Corte simples', points_cost: 300 });

export function makeWallet(userId: string, extra: Partial<Wallet> = {}): Wallet {
  return {
    id: `w-${userId}`,
    user_id: userId,
    balance: 0,
    lifetime_points: 0,
    updated_at: '2026-11-26T12:00:00Z',
    full_name: `Cliente ${userId}`,
    email: `${userId}@x.com`,
    ...extra,
  };
}

export const ANA = makeWallet('u1', { full_name: 'Ana Lima', email: 'ana@x.com', balance: 120, lifetime_points: 300 });
export const BRUNO = makeWallet('u2', { full_name: 'Bruno Reis', email: 'bruno@x.com', balance: 40, lifetime_points: 40 });

/** A resposta do /add e do /remove: a carteira sem o cliente. */
export function walletResponse(wallet: Wallet, balance: number, lifetimePoints = wallet.lifetime_points) {
  const { full_name: _name, email: _email, ...rest } = wallet;
  return { ...rest, balance, lifetime_points: lifetimePoints };
}

export function makeRedemption(id: string, wallet: Wallet, reward: Reward, redeemedAt = '2026-11-26T17:30:00Z'): Redemption {
  return {
    id,
    wallet_id: wallet.id,
    user_id: wallet.user_id,
    reward_id: reward.id,
    points_spent: reward.points_cost,
    redeemed_at: redeemedAt,
    reward,
  };
}
