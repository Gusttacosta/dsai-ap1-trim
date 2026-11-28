import { useCallback } from 'react';
import api from '../api';
import { upsert } from './useNameList';
import { useApiResource } from './useApiResource';

// Fidelidade no painel do admin: prêmios, carteiras com o ajuste manual de pontos e o histórico
// de resgates, com as rotas de /loyalty (SPEC/2026-11-26-painel-fidelidade.md). As ações devolvem
// o que o backend gravou e lançam o erro da API, para quem chamou mostrar a mensagem.

export type Reward = {
  id: string;
  name: string;
  description: string | null;
  points_cost: number;
  is_active: boolean;
  created_at: string;
};

/** Campos da criação, já no formato da API. */
export type RewardInput = Pick<Reward, 'name' | 'description' | 'points_cost'>;
/** Alteração parcial: só os campos que mudaram. */
export type RewardChanges = Partial<RewardInput>;

export type Wallet = {
  id: string;
  user_id: string;
  balance: number;
  lifetime_points: number;
  updated_at: string;
  full_name: string;
  email: string;
};

export type Redemption = {
  id: string;
  wallet_id: string;
  user_id: string;
  reward_id: string;
  points_spent: number;
  redeemed_at: string;
  reward: Reward;
};

/** Adicionar ou retirar pontos: o fim da rota (`/wallet/{id}/add` ou `/remove`). */
export type AdjustAction = 'add' | 'remove';

/** Mesma ordem do backend: do prêmio mais barato para o mais caro. */
const byCost = (a: Reward, b: Reward) => a.points_cost - b.points_cost;

/** Mesma ordem do backend: do maior saldo para o menor, e pelo nome. */
const byBalance = (a: Wallet, b: Wallet) => b.balance - a.balance || a.full_name.localeCompare(b.full_name, 'pt-BR');

const loadRewards = async () => (await api.get<Reward[]>('/loyalty/rewards')).data;
const loadWallets = async () => (await api.get<Wallet[]>('/loyalty/wallets')).data;
const loadRedemptions = async () => (await api.get<Redemption[]>('/loyalty/redemptions')).data;

export function useAdminRewards() {
  const { data: rewards, setData, status, loadError, reload } = useApiResource(
    loadRewards,
    [] as Reward[],
    'Não foi possível carregar os prêmios.',
  );

  const createReward = useCallback(
    async (input: RewardInput) => {
      const saved = (await api.post<Reward>('/loyalty/rewards', input)).data;
      setData((current) => upsert(current, saved, byCost));
      return saved;
    },
    [setData],
  );

  /** O PUT com `is_active: false` desativa: o prêmio sai desta lista, que só tem os ativos. */
  const updateReward = useCallback(
    async (id: string, changes: RewardChanges | { is_active: false }) => {
      const saved = (await api.put<Reward>(`/loyalty/rewards/${id}`, changes)).data;
      setData((current) =>
        saved.is_active ? upsert(current, saved, byCost) : current.filter((r) => r.id !== saved.id),
      );
      return saved;
    },
    [setData],
  );

  const deactivateReward = useCallback((id: string) => updateReward(id, { is_active: false }), [updateReward]);

  return { rewards, status, loadError, reload, createReward, updateReward, deactivateReward };
}

export function useWallets() {
  const { data: wallets, setData, status, loadError, reload } = useApiResource(
    loadWallets,
    [] as Wallet[],
    'Não foi possível carregar as carteiras.',
  );

  /** Ajusta o saldo com o motivo. A resposta não traz o cliente: ele continua o da linha. */
  const adjust = useCallback(
    async (wallet: Wallet, action: AdjustAction, points: number, reason: string) => {
      const { data } = await api.post<Omit<Wallet, 'full_name' | 'email'>>(
        `/loyalty/wallet/${wallet.user_id}/${action}`,
        null,
        { params: { points, reason } },
      );
      const saved: Wallet = { ...wallet, ...data };
      setData((current) => upsert(current, saved, byBalance));
      return saved;
    },
    [setData],
  );

  return { wallets, status, loadError, reload, adjust };
}

export function useRedemptions() {
  const { data: redemptions, status, loadError, reload } = useApiResource(
    loadRedemptions,
    [] as Redemption[],
    'Não foi possível carregar os resgates.',
  );
  return { redemptions, status, loadError, reload };
}
