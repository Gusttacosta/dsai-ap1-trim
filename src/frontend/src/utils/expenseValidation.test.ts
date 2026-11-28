import { describe, expect, it } from 'vitest';
import {
  AMOUNT_ERROR,
  CATEGORY_NAME_ERROR,
  DATE_ERROR,
  DESCRIPTION_ERROR,
  formatPaymentDate,
  parseAmount,
  validateAmount,
  validateCategoryName,
  validateDescription,
  validatePaymentDate,
} from './expenseValidation';

// SPEC/2026-11-26-painel-despesas.md: as mesmas regras do backend, antes da API.

describe('parseAmount', () => {
  it.each([
    ['100', '100.00'],
    ['100,5', '100.50'],
    ['0,01', '0.01'],
    ['99999999,99', '99999999.99'],
  ])('%s vira %s', (text, amount) => {
    expect(parseAmount(text)).toBe(amount);
    expect(validateAmount(text)).toBeNull();
  });

  it.each(['', '0', '0,00', '-5', '10,555', '100000000', 'abc', '1.000,00'])('recusa %j', (text) => {
    expect(parseAmount(text)).toBeNull();
    expect(validateAmount(text)).toBe(AMOUNT_ERROR);
  });
});

describe('textos', () => {
  it('descrição aparada, de 1 a 255', () => {
    expect(validateDescription('  Aluguel ')).toBeNull();
    expect(validateDescription('x'.repeat(255))).toBeNull();
    expect(validateDescription('   ')).toBe(DESCRIPTION_ERROR);
    expect(validateDescription('x'.repeat(256))).toBe(DESCRIPTION_ERROR);
  });

  it('nome da categoria aparado, de 1 a 100', () => {
    expect(validateCategoryName(' Luz ')).toBeNull();
    expect(validateCategoryName('')).toBe(CATEGORY_NAME_ERROR);
    expect(validateCategoryName('x'.repeat(101))).toBe(CATEGORY_NAME_ERROR);
  });
});

describe('data', () => {
  it('exige a data do campo', () => {
    expect(validatePaymentDate('2026-11-20')).toBeNull();
    expect(validatePaymentDate('')).toBe(DATE_ERROR);
  });

  it('mostra no formato brasileiro, sem mudar de dia', () => {
    expect(formatPaymentDate('2026-11-01')).toBe('01/11/2026');
  });
});
