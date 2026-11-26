import { parsePositiveInt } from './textValidation';

// Estoque no painel: os tipos de movimentação com o sinal, o aviso de estoque baixo e as regras
// do formulário (src/backend/modules/products/schemas.py; SPEC/2026-11-26-painel-estoque.md).
// Cada validate* devolve a mensagem de erro, ou null quando o valor serve.

export type MovementType = 'sale' | 'restock' | 'loss' | 'adjustment';

/** Teto da tela: o backend não tem, e a coluna é Integer. */
export const QUANTITY_MAX = 10_000;
/** Até quantas unidades um produto ativo está com estoque baixo. */
export const LOW_STOCK_MAX = 5;
export const NOTES_MAX = 500;

export const QUANTITY_ERROR = 'Quantidade deve ser um número inteiro de 1 a 10.000';
export const NOTES_ERROR = `Observação deve ter até ${NOTES_MAX} caracteres`;

/** Uma opção do formulário: o tipo da API e o lado (entrada soma, saída subtrai). */
export type MovementOption = {
  key: string;
  type: MovementType;
  direction: 1 | -1;
  label: string;
  /** O nome do tipo na pergunta de confirmação: "Registrar saída de 2 un de Pomada (venda)?" */
  short: string;
};

export const MOVEMENT_OPTIONS: MovementOption[] = [
  { key: 'restock', type: 'restock', direction: 1, label: 'Entrada: reposição', short: 'reposição' },
  { key: 'adjustment-in', type: 'adjustment', direction: 1, label: 'Entrada: ajuste de inventário', short: 'ajuste de inventário' },
  { key: 'sale', type: 'sale', direction: -1, label: 'Saída: venda', short: 'venda' },
  { key: 'loss', type: 'loss', direction: -1, label: 'Saída: perda ou avaria', short: 'perda ou avaria' },
  { key: 'adjustment-out', type: 'adjustment', direction: -1, label: 'Saída: ajuste de inventário', short: 'ajuste de inventário' },
];

/** O produto desativado não vende nem recebe reposição: só perda e ajuste (#61). */
export function movementOptions(isActive: boolean): MovementOption[] {
  return isActive ? MOVEMENT_OPTIONS : MOVEMENT_OPTIONS.filter((o) => o.type === 'loss' || o.type === 'adjustment');
}

export const MOVEMENT_LABELS: Record<MovementType, string> = {
  restock: 'Reposição',
  sale: 'Venda',
  loss: 'Perda',
  adjustment: 'Ajuste',
};

/** "12 un" */
export const formatUnits = (quantity: number) => `${quantity.toLocaleString('pt-BR')} un`;

/** A quantidade da movimentação com o sinal: "+10 un", "-2 un". */
export const formatSignedUnits = (quantity: number) => `${quantity > 0 ? '+' : '-'}${formatUnits(Math.abs(quantity))}`;

/** Aviso do estoque de um produto: só os ativos com até LOW_STOCK_MAX unidades têm. */
export function stockWarning(product: { is_active: boolean; stock_quantity: number }): string | null {
  if (!product.is_active || product.stock_quantity > LOW_STOCK_MAX) return null;
  return product.stock_quantity === 0 ? 'Sem estoque' : 'Estoque baixo';
}

/** "2 produtos com estoque baixo ou zerado: Óleo, Pomada.", ou null sem nenhum. */
export function lowStockSummary(products: { name: string; is_active: boolean; stock_quantity: number }[]): string | null {
  const names = products.filter((p) => stockWarning(p) !== null).map((p) => p.name);
  if (names.length === 0) return null;
  const subject = names.length === 1 ? '1 produto' : `${names.length} produtos`;
  return `${subject} com estoque baixo ou zerado: ${names.join(', ')}.`;
}

export const parseQuantity = (text: string): number | null => parsePositiveInt(text, QUANTITY_MAX);

export function validateQuantity(text: string): string | null {
  return parseQuantity(text) === null ? QUANTITY_ERROR : null;
}

/** A observação é opcional: vazia serve. */
export function validateNotes(text: string): string | null {
  return text.trim().length <= NOTES_MAX ? null : NOTES_ERROR;
}

/** A saída não pode passar do estoque (o backend recusaria com 400). */
export function validateStock(option: MovementOption, quantity: number, stock: number): string | null {
  return option.direction < 0 && quantity > stock ? `Estoque insuficiente: há só ${formatUnits(stock)}.` : null;
}

/** "Registrar saída de 2 un de Pomada (perda ou avaria)? O estoque passa de 10 para 8 un." */
export function movementQuestion(productName: string, stock: number, option: MovementOption, quantity: number): string {
  const side = option.direction > 0 ? 'entrada' : 'saída';
  const after = stock + option.direction * quantity;
  return (
    `Registrar ${side} de ${formatUnits(quantity)} de ${productName} (${option.short})? ` +
    `O estoque passa de ${stock.toLocaleString('pt-BR')} para ${formatUnits(after)}.`
  );
}
