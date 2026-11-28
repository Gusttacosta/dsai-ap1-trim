import type { Subscription, SubscriptionPlan } from '../hooks/useTrimClub';

// Planos e assinaturas como a API os devolve, para os testes do Trim Club
// (SPEC/2026-11-26-painel-trim-club.md).

export function makePlan(id: string, extra: Partial<SubscriptionPlan> = {}): SubscriptionPlan {
  return {
    id,
    name: `Plano ${id}`,
    description: null,
    monthly_price: '50.00',
    included_cuts: 2,
    included_shaves: 0,
    discount_percentage: '0.00',
    is_active: true,
    ...extra,
  };
}

export const BASICO = makePlan('basico', { name: 'Básico', monthly_price: '49.90' });
export const OURO = makePlan('ouro', {
  name: 'Ouro',
  description: 'Bebida premium',
  monthly_price: '150.00',
  included_cuts: null,
  included_shaves: 2,
  discount_percentage: '10.00',
});

export function makeSubscription(id: string, extra: Partial<Subscription> = {}): Subscription {
  return {
    id,
    user_id: `u-${id}`,
    plan_id: OURO.id,
    start_date: '2026-11-26',
    end_date: '2026-12-26',
    status: 'active',
    plan: OURO,
    ...extra,
  };
}
