// Validação dos campos do barbeiro e da escala no painel, com as regras e as mensagens do backend
// (src/backend/modules/barbers/schemas.py; SPEC/2026-11-26-painel-barbeiros.md). Cada validate*
// devolve a mensagem de erro, ou null quando o valor serve.

import { parsePrice } from './serviceValidation';

export const BIO_MAX = 500;
export const COMMISSION_ERROR = 'Comissão deve ser um valor entre 0 e 100, com até 2 casas decimais';
export const BIO_ERROR = `A bio deve ter até ${BIO_MAX} caracteres`;
export const INSTAGRAM_ERROR = 'Informe o endereço completo do Instagram, começando com https://';

/** Comissão digitada ("50", "12,5") no formato da API ("12.50"), ou null fora de 0 a 100. */
export function parseCommission(text: string): string | null {
  // Mesmo formato do preço: dígitos, vírgula ou ponto, até 2 casas.
  const value = parsePrice(text);
  return value !== null && Number(value) <= 100 ? value : null;
}

export function validateCommission(text: string): string | null {
  return parseCommission(text) === null ? COMMISSION_ERROR : null;
}

export function validateBio(text: string): string | null {
  return text.trim().length > BIO_MAX ? BIO_ERROR : null;
}

/** Vazio (sem Instagram) ou um endereço http(s) com algo depois do "//". */
export function validateInstagram(text: string): string | null {
  const value = text.trim();
  return value === '' || /^https?:\/\/\S+$/i.test(value) ? null : INSTAGRAM_ERROR;
}

// ── Escala ───────────────────────────────────────────────

export const DAY_NAMES = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];

export const END_BEFORE_START = 'O horário de término deve ser após o início.';
export const INCOMPLETE_BREAK = 'Informe o início e o fim do almoço, ou nenhum dos dois.';
export const BREAK_INVERTED = 'O fim do almoço deve ser após o início do almoço.';
export const BREAK_OUTSIDE = 'O almoço deve ficar dentro do expediente.';

/** Um dia como os campos de hora mostram ("09:00"); almoço vazio é ''. */
export type DayFields = {
  day_of_week: number;
  is_working: boolean;
  start_time: string;
  end_time: string;
  break_start: string;
  break_end: string;
};

/**
 * Confere um dia na ordem do backend (check_work_day). Os horários "HH:MM" comparam como texto.
 * Vale também para o dia de folga: o backend confere os horários dele do mesmo jeito.
 */
export function validateDay(day: DayFields): string | null {
  if (!day.start_time || !day.end_time || day.end_time <= day.start_time) return END_BEFORE_START;
  if (!day.break_start !== !day.break_end) return INCOMPLETE_BREAK;
  if (!day.break_start) return null;
  if (day.break_end <= day.break_start) return BREAK_INVERTED;
  if (day.break_start < day.start_time || day.break_end > day.end_time) return BREAK_OUTSIDE;
  return null;
}

/** O primeiro problema da semana, com o nome do dia ("Terça: ..."), ou null. */
export function validateWeek(days: DayFields[]): string | null {
  for (const day of days) {
    const problem = validateDay(day);
    if (problem) return `${DAY_NAMES[day.day_of_week]}: ${problem}`;
  }
  return null;
}
