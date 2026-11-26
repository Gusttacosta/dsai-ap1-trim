import { describe, expect, it } from 'vitest';
import {
  MOVEMENT_OPTIONS,
  NOTES_ERROR,
  QUANTITY_ERROR,
  formatSignedUnits,
  formatUnits,
  lowStockSummary,
  movementOptions,
  movementQuestion,
  parseQuantity,
  stockWarning,
  validateNotes,
  validateQuantity,
  validateStock,
} from './inventory';
import { parsePositiveInt } from './textValidation';

// SPEC/2026-11-26-painel-estoque.md: as regras do estoque conferidas na tela.

const option = (key: string) => MOVEMENT_OPTIONS.find((o) => o.key === key)!;

describe('parsePositiveInt', () => {
  it.each([
    ['1', 1],
    [' 12 ', 12],
    ['50', 50],
  ])('aceita %j até o teto', (text, value) => {
    expect(parsePositiveInt(text, 50)).toBe(value);
  });

  it.each(['', '0', '-3', '+3', '1,5', '1.5', 'dez', '51', '1 0'])('recusa %j', (text) => {
    expect(parsePositiveInt(text, 50)).toBeNull();
  });
});

describe('quantidade e observação', () => {
  it('a quantidade vai de 1 a 10.000', () => {
    expect(parseQuantity('10000')).toBe(10_000);
    expect(validateQuantity('10000')).toBeNull();
    expect(validateQuantity('10001')).toBe(QUANTITY_ERROR);
    expect(validateQuantity('0')).toBe(QUANTITY_ERROR);
    expect(validateQuantity('')).toBe(QUANTITY_ERROR);
  });

  it('a observação é opcional e tem até 500 caracteres, sem contar as pontas', () => {
    expect(validateNotes('')).toBeNull();
    expect(validateNotes(` ${'a'.repeat(500)} `)).toBeNull();
    expect(validateNotes('a'.repeat(501))).toBe(NOTES_ERROR);
  });

  it('a saída não passa do estoque; a entrada não tem limite de estoque', () => {
    expect(validateStock(option('loss'), 4, 3)).toBe('Estoque insuficiente: há só 3 un.');
    expect(validateStock(option('adjustment-out'), 3, 3)).toBeNull();
    expect(validateStock(option('restock'), 40, 0)).toBeNull();
  });
});

describe('tipos de movimentação', () => {
  it('o sinal sai do tipo: reposição soma, venda e perda subtraem, ajuste vai para os dois lados', () => {
    expect(MOVEMENT_OPTIONS.map((o) => [o.type, o.direction])).toEqual([
      ['restock', 1],
      ['adjustment', 1],
      ['sale', -1],
      ['loss', -1],
      ['adjustment', -1],
    ]);
  });

  it('o produto desativado só oferece perda e ajuste', () => {
    expect(movementOptions(true)).toHaveLength(5);
    expect(movementOptions(false).map((o) => o.key)).toEqual(['adjustment-in', 'loss', 'adjustment-out']);
  });

  it('a pergunta diz o lado, o tipo e o estoque antes e depois', () => {
    expect(movementQuestion('Pomada', 10, option('loss'), 2)).toBe(
      'Registrar saída de 2 un de Pomada (perda ou avaria)? O estoque passa de 10 para 8 un.',
    );
    expect(movementQuestion('Óleo', 1200, option('restock'), 30)).toBe(
      'Registrar entrada de 30 un de Óleo (reposição)? O estoque passa de 1.200 para 1.230 un.',
    );
  });
});

describe('estoque baixo', () => {
  it.each([
    [true, 0, 'Sem estoque'],
    [true, 1, 'Estoque baixo'],
    [true, 5, 'Estoque baixo'],
    [true, 6, null],
    [false, 0, null],
  ])('ativo %s com %i un: %j', (isActive, stock, warning) => {
    expect(stockWarning({ is_active: isActive, stock_quantity: stock })).toBe(warning);
  });

  it('o resumo lista só os ativos que precisam de reposição', () => {
    const products = [
      { name: 'Óleo', is_active: true, stock_quantity: 0 },
      { name: 'Pente', is_active: false, stock_quantity: 0 },
      { name: 'Pomada', is_active: true, stock_quantity: 3 },
      { name: 'Shampoo', is_active: true, stock_quantity: 20 },
    ];
    expect(lowStockSummary(products)).toBe('2 produtos com estoque baixo ou zerado: Óleo, Pomada.');
    expect(lowStockSummary(products.slice(0, 2))).toBe('1 produto com estoque baixo ou zerado: Óleo.');
    expect(lowStockSummary(products.slice(3))).toBeNull();
  });
});

describe('unidades', () => {
  it('formata com o milhar e o sinal', () => {
    expect(formatUnits(1200)).toBe('1.200 un');
    expect(formatSignedUnits(10)).toBe('+10 un');
    expect(formatSignedUnits(-2)).toBe('-2 un');
  });
});
