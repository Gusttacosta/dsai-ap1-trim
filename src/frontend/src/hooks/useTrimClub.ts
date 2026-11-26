import { isAxiosError } from 'axios';
import { useCallback } from 'react';
import api from '../api';
import type { SubscriptionStatus } from '../utils/trimClub';
import { upsert } from './useNameList';
import { useApiResource } from './useApiResource';

// Trim Club no painel do admin (planos e assinantes) e na conta do cliente (a assinatura dele),
// com as rotas de /subscriptions (SPEC/2026-11-26-painel-trim-club.md). As ações devolvem o que o
// backend gravou e lançam o erro da API, para quem chamou mostrar a mensagem.

export type SubscriptionPlan = {
  id: string;
  name: string;
  description: string | null;
  /** O backend serializa o Decimal como texto ("49.90"). */
  monthly_price: string;
  /** null = ilimitado, 0 = não incluso (#16). */
  included_cuts: number | null;
  included_shaves: number | null;
  discount_percentage: string;
  is_active: boolean;
};

/** Campos da criação, já no formato da API. */
export type PlanInput = Pick<
  SubscriptionPlan,
  'name' | 'description' | 'monthly_price' | 'included_cuts' | 'included_shaves' | 'discount_percentage'
>;
/** Alteração parcial: só os campos que mudaram. */
export type PlanChanges = Partial<PlanInput>;

export type Subscription = {
  id: string;
  user_id: string;
  plan_id: string;
  /** "AAAA-MM-DD" */
  start_date: string;
  end_date: string;
  status: SubscriptionStatus;
  plan: SubscriptionPlan;
};

/** Nome e e-mail do assinante; null quando a consulta falhou. */
export type Subscriber = { full_name: string; email: string } | null;

/** Mesma ordem do backend: do plano mais barato para o mais caro. */
const byPrice = (a: SubscriptionPlan, b: SubscriptionPlan) => Number(a.monthly_price) - Number(b.monthly_price);

const loadPlans = async () => (await api.get<SubscriptionPlan[]>('/subscriptions/plans')).data;

export function useAdminPlans() {
  const { data: plans, setData, status, loadError, reload } = useApiResource(
    loadPlans,
    [] as SubscriptionPlan[],
    'Não foi possível carregar os planos.',
  );

  const store = useCallback(
    (saved: SubscriptionPlan) => {
      setData((current) => upsert(current, saved, byPrice));
      return saved;
    },
    [setData],
  );

  const createPlan = useCallback(
    async (input: PlanInput) => store((await api.post<SubscriptionPlan>('/subscriptions/plans', input)).data),
    [store],
  );

  const updatePlan = useCallback(
    async (id: string, changes: PlanChanges) =>
      store((await api.put<SubscriptionPlan>(`/subscriptions/plans/${id}`, changes)).data),
    [store],
  );

  /** O DELETE só desativa: o plano sai da vitrine e desta lista, que só tem os ativos. */
  const removePlan = useCallback(
    async (id: string) => {
      await api.delete(`/subscriptions/plans/${id}`);
      setData((current) => current.filter((p) => p.id !== id));
    },
    [setData],
  );

  return { plans, status, loadError, reload, createPlan, updatePlan, removePlan };
}

type Loaded = { subscriptions: Subscription[]; subscribers: Record<string, Subscriber> };

/** Nome e e-mail de cada assinante. Uma consulta que falha não impede a lista. */
async function loadSubscribers(userIds: string[]): Promise<Record<string, Subscriber>> {
  const unique = [...new Set(userIds)];
  const results = await Promise.allSettled(unique.map((id) => api.get<Subscriber>(`/auth/users/${id}`)));
  return Object.fromEntries(
    unique.map((id, i) => {
      const result = results[i];
      return [id, result.status === 'fulfilled' ? result.value.data : null];
    }),
  );
}

async function loadSubscriptions(): Promise<Loaded> {
  const subscriptions = (await api.get<Subscription[]>('/subscriptions/users')).data;
  return { subscriptions, subscribers: await loadSubscribers(subscriptions.map((s) => s.user_id)) };
}

const NO_SUBSCRIPTIONS: Loaded = { subscriptions: [], subscribers: {} };

export function useSubscriptions() {
  const { data, status, loadError, reload } = useApiResource(
    loadSubscriptions,
    NO_SUBSCRIPTIONS,
    'Não foi possível carregar os assinantes.',
  );
  return { ...data, status, loadError, reload };
}

/** A assinatura do cliente logado, ou null quando ele não tem (404). */
async function loadMine(): Promise<Subscription | null> {
  try {
    return (await api.get<Subscription>('/subscriptions/me')).data;
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
}

export function useMySubscription() {
  const { data: subscription, setData, status, loadError, reload } = useApiResource(
    loadMine,
    null as Subscription | null,
    'Não foi possível carregar sua assinatura.',
  );

  /** Cancela e passa a mostrar a assinatura como o backend devolveu ("canceled"). */
  const cancel = useCallback(async () => {
    const saved = (await api.put<Subscription>('/subscriptions/me/cancel')).data;
    setData(saved);
    return saved;
  }, [setData]);

  return { subscription, status, loadError, reload, cancel };
}
