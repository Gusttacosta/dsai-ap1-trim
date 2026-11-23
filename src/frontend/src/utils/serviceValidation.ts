// Validação e conversão dos campos do formulário de serviço do painel, com as regras do
// backend (src/backend/modules/services/schemas.py; SPEC/2026-11-23-painel-servicos.md).
// Cada validate* devolve a mensagem de erro, ou null quando o valor serve.

export const NAME_MIN = 2;
export const NAME_MAX = 100;
export const DURATION_MAX = 720;
/** Maior parte inteira do preço que cabe no Numeric(10, 2) da coluna. */
const PRICE_INT_MAX = 99_999_999;

// Só dígitos, com um separador decimal (vírgula ou ponto) e até 2 casas. Sem milhar.
const PRICE_FORMAT = /^(\d+)(?:[.,](\d{1,2}))?$/;

export const NAME_ERROR = `Nome deve ter entre ${NAME_MIN} e ${NAME_MAX} caracteres`;
export const PRICE_ERROR = 'Preço deve ser um valor entre 0 e 99.999.999,99, com até 2 casas decimais';
export const DURATION_ERROR = `Duração deve ser um número inteiro de 1 a ${DURATION_MAX} minutos`;

export function validateServiceName(name: string): string | null {
  const length = name.trim().length;
  return length < NAME_MIN || length > NAME_MAX ? NAME_ERROR : null;
}

/**
 * Preço digitado ("35", "35,5", "35.50") no formato da API, com 2 casas ("35.50"),
 * ou null quando não serve. Converte o texto sem passar por float, para não arredondar.
 */
export function parsePrice(text: string): string | null {
  const match = PRICE_FORMAT.exec(text.trim());
  if (!match) return null;
  const integer = match[1].replace(/^0+(?=\d)/, '');
  if (integer.length > String(PRICE_INT_MAX).length || Number(integer) > PRICE_INT_MAX) return null;
  return `${integer}.${(match[2] ?? '').padEnd(2, '0')}`;
}

export function validatePrice(text: string): string | null {
  return parsePrice(text) === null ? PRICE_ERROR : null;
}

/** Duração digitada como inteiro, ou null quando não é um inteiro de 1 a 720. */
export function parseDuration(text: string): number | null {
  const value = text.trim();
  if (!/^\d+$/.test(value)) return null;
  const minutes = Number(value);
  return minutes >= 1 && minutes <= DURATION_MAX ? minutes : null;
}

export function validateDuration(text: string): string | null {
  return parseDuration(text) === null ? DURATION_ERROR : null;
}

/** Preço da API ("35.00" ou 35) para mostrar no campo do formulário ("35,00"). */
export function priceToInput(price: string | number): string {
  return Number(price).toFixed(2).replace('.', ',');
}

/** Preço da API para a tabela, em reais ("R$ 35,00"). */
export function formatPrice(price: string | number): string {
  return Number(price).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
