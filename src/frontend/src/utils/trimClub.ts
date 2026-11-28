import { fitsTrimmed } from './textValidation';
import { parsePrice } from './serviceValidation';

// Planos e assinaturas do Trim Club na tela: os benefícios do plano, usados pela vitrine, pelo
// painel e pela conta, a situação da assinatura e a validação do formulário de plano, com as
// regras do backend (src/backend/modules/subscriptions/schemas.py;
// SPEC/2026-11-26-painel-trim-club.md). Cada validate* devolve a mensagem de erro, ou null.

export const PLAN_NAME_MAX = 100;
export const QUANTITY_MAX = 999;

export const PLAN_NAME_ERROR = `Nome do plano deve ter entre 1 e ${PLAN_NAME_MAX} caracteres`;
export const MONTHLY_PRICE_ERROR = 'Preço mensal deve ser maior que zero, com até 2 casas decimais';
export const DISCOUNT_ERROR = 'Desconto deve ser de 0 a 100%, com até 2 casas decimais';
export const quantityError = (label: string) => `${label} deve ser um número inteiro de 0 a ${QUANTITY_MAX}`;

export type SubscriptionStatus = 'active' | 'canceled' | 'past_due';

export const SUBSCRIPTION_STATUS_LABELS: Record<SubscriptionStatus, string> = {
  active: 'Ativa',
  canceled: 'Cancelada',
  past_due: 'Vencida',
};

/** O que os benefícios precisam do plano. */
export type PlanBenefitsSource = {
  included_cuts: number | null;
  included_shaves: number | null;
  discount_percentage?: string | number;
};

/** "Ilimitados", "2 por mês" ou nada, quando o plano não inclui o serviço (#16). */
export function quantityLabel(value: number | null): string | null {
  if (value === null) return 'Ilimitados';
  return value > 0 ? `${value} por mês` : null;
}

/** Cortes e barbas inclusos, como frases: ["Cortes: Ilimitados", "Barbas: 2 por mês"]. */
export function planBenefits(plan: PlanBenefitsSource): string[] {
  const lines: string[] = [];
  const cuts = quantityLabel(plan.included_cuts);
  const shaves = quantityLabel(plan.included_shaves);
  if (cuts) lines.push(`Cortes: ${cuts}`);
  if (shaves) lines.push(`Barbas: ${shaves}`);
  return lines;
}

/** Os benefícios e, quando há, o desconto ("Desconto: 10%"). */
export function planBenefitsWithDiscount(plan: PlanBenefitsSource): string[] {
  const discount = Number(plan.discount_percentage ?? 0);
  if (discount <= 0) return planBenefits(plan);
  return [...planBenefits(plan), `Desconto: ${discount.toLocaleString('pt-BR')}%`];
}

export function validatePlanName(name: string): string | null {
  return fitsTrimmed(name, PLAN_NAME_MAX) ? null : PLAN_NAME_ERROR;
}

/** Preço mensal no formato da API ("49.90"), ou null quando não é maior que zero. */
export function parseMonthlyPrice(text: string): string | null {
  const price = parsePrice(text);
  return price !== null && Number(price) > 0 ? price : null;
}

export function validateMonthlyPrice(text: string): string | null {
  return parseMonthlyPrice(text) === null ? MONTHLY_PRICE_ERROR : null;
}

/** Quantidade inclusa: inteiro de 0 a 999, ou null quando não serve. */
export function parseQuantity(text: string): number | null {
  const value = text.trim();
  if (!/^\d+$/.test(value)) return null;
  const quantity = Number(value);
  return quantity <= QUANTITY_MAX ? quantity : null;
}

/** Ilimitado dispensa a quantidade. */
export function validateQuantity(text: string, unlimited: boolean, label: string): string | null {
  return unlimited || parseQuantity(text) !== null ? null : quantityError(label);
}

/** Desconto no formato da API ("10.00"); vazio é zero. null quando passa de 100. */
export function parseDiscount(text: string): string | null {
  if (!text.trim()) return '0.00';
  const discount = parsePrice(text);
  return discount !== null && Number(discount) <= 100 ? discount : null;
}

export function validateDiscount(text: string): string | null {
  return parseDiscount(text) === null ? DISCOUNT_ERROR : null;
}
