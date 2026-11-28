import { parsePrice } from './serviceValidation';
import { fitsTrimmed as fits } from './textValidation';

// Validação e conversão dos campos de despesa e de categoria do painel, com as regras do
// backend (src/backend/modules/expenses/schemas.py; SPEC/2026-11-26-painel-despesas.md).
// Cada validate* devolve a mensagem de erro, ou null quando o valor serve.

export const DESCRIPTION_MAX = 255;
export const CATEGORY_NAME_MAX = 100;

export const DESCRIPTION_ERROR = `Descrição deve ter entre 1 e ${DESCRIPTION_MAX} caracteres`;
export const AMOUNT_ERROR = 'Valor deve ser maior que 0 e até 99.999.999,99, com até 2 casas decimais';
export const DATE_ERROR = 'Informe a data do pagamento';
export const CATEGORY_NAME_ERROR = `Nome da categoria deve ter entre 1 e ${CATEGORY_NAME_MAX} caracteres`;

export function validateDescription(text: string): string | null {
  return fits(text, DESCRIPTION_MAX) ? null : DESCRIPTION_ERROR;
}

export function validateCategoryName(text: string): string | null {
  return fits(text, CATEGORY_NAME_MAX) ? null : CATEGORY_NAME_ERROR;
}

/** Valor digitado no formato da API ("100.50"), ou null quando não é maior que 0 ou não cabe. */
export function parseAmount(text: string): string | null {
  const amount = parsePrice(text);
  return amount !== null && Number(amount) > 0 ? amount : null;
}

export function validateAmount(text: string): string | null {
  return parseAmount(text) === null ? AMOUNT_ERROR : null;
}

/** O campo de data entrega "AAAA-MM-DD", ou vazio quando não foi preenchido. */
export function validatePaymentDate(date: string): string | null {
  return /^\d{4}-\d{2}-\d{2}$/.test(date) ? null : DATE_ERROR;
}

/** "2026-11-20" como na tabela: "20/11/2026". Sem passar por Date, para não mudar de dia. */
export function formatPaymentDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-');
  return `${day}/${month}/${year}`;
}
