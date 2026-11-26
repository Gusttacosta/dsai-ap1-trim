import { describe, expect, it } from 'vitest';
import {
  DISCOUNT_ERROR,
  MONTHLY_PRICE_ERROR,
  PLAN_NAME_ERROR,
  parseDiscount,
  parseMonthlyPrice,
  parseQuantity,
  planBenefits,
  planBenefitsWithDiscount,
  quantityError,
  quantityLabel,
  validateDiscount,
  validateMonthlyPrice,
  validatePlanName,
  validateQuantity,
} from './trimClub';

// SPEC/2026-11-26-painel-trim-club.md: benefícios do plano e as regras do formulário de plano.

describe('benefícios do plano', () => {
  it('null é ilimitado, 0 não aparece e n vira "n por mês" (#16)', () => {
    expect([quantityLabel(null), quantityLabel(0), quantityLabel(2)]).toEqual(['Ilimitados', null, '2 por mês']);
  });

  it('junta cortes e barbas e deixa de fora o que o plano não inclui', () => {
    expect(planBenefits({ included_cuts: null, included_shaves: 2 })).toEqual(['Cortes: Ilimitados', 'Barbas: 2 por mês']);
    expect(planBenefits({ included_cuts: 0, included_shaves: 0 })).toEqual([]);
  });

  it('o desconto entra só quando é maior que zero', () => {
    expect(planBenefitsWithDiscount({ included_cuts: 2, included_shaves: 0, discount_percentage: '10.50' })).toEqual([
      'Cortes: 2 por mês',
      'Desconto: 10,5%',
    ]);
    expect(planBenefitsWithDiscount({ included_cuts: 2, included_shaves: 0, discount_percentage: '0.00' })).toEqual([
      'Cortes: 2 por mês',
    ]);
  });
});

describe('validação do plano', () => {
  it('nome de 1 a 100 caracteres sem contar as pontas', () => {
    expect(validatePlanName('  Ouro  ')).toBeNull();
    expect(validatePlanName('   ')).toBe(PLAN_NAME_ERROR);
    expect(validatePlanName('x'.repeat(101))).toBe(PLAN_NAME_ERROR);
  });

  it('preço mensal maior que zero, com vírgula ou ponto', () => {
    expect(parseMonthlyPrice('49,9')).toBe('49.90');
    expect(validateMonthlyPrice('0')).toBe(MONTHLY_PRICE_ERROR);
    expect(validateMonthlyPrice('0,00')).toBe(MONTHLY_PRICE_ERROR);
    expect(validateMonthlyPrice('abc')).toBe(MONTHLY_PRICE_ERROR);
    expect(validateMonthlyPrice('10,999')).toBe(MONTHLY_PRICE_ERROR);
  });

  it('quantidade inteira de 0 a 999, dispensada quando é ilimitada', () => {
    expect(parseQuantity(' 4 ')).toBe(4);
    expect(parseQuantity('0')).toBe(0);
    expect(parseQuantity('-1')).toBeNull();
    expect(parseQuantity('1.5')).toBeNull();
    expect(parseQuantity('1000')).toBeNull();
    expect(validateQuantity('', false, 'Cortes inclusos')).toBe(quantityError('Cortes inclusos'));
    expect(validateQuantity('', true, 'Cortes inclusos')).toBeNull();
    expect(quantityError('Barbas inclusas')).toBe('Barbas inclusas deve ser um número inteiro de 0 a 999');
  });

  it('desconto de 0 a 100%; vazio é zero', () => {
    expect(parseDiscount('')).toBe('0.00');
    expect(parseDiscount('12,5')).toBe('12.50');
    expect(parseDiscount('100')).toBe('100.00');
    expect(validateDiscount('100,01')).toBe(DISCOUNT_ERROR);
    expect(validateDiscount('-5')).toBe(DISCOUNT_ERROR);
  });
});
