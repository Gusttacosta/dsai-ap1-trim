import { describe, expect, it } from 'vitest';
import {
  DURATION_ERROR,
  NAME_ERROR,
  PRICE_ERROR,
  formatPrice,
  parseDuration,
  parsePrice,
  priceToInput,
  validateDuration,
  validatePrice,
  validateServiceName,
} from './serviceValidation';

// SPEC/2026-11-23-painel-servicos.md: as mesmas regras do backend (services/schemas.py).

describe('validateServiceName', () => {
  it.each(['Co', 'Corte', '  Barba  ', 'x'.repeat(100), ` ${'x'.repeat(100)} `])('aceita %j', (name) => {
    expect(validateServiceName(name)).toBeNull();
  });

  it.each(['', '   ', 'C', ' C ', 'x'.repeat(101)])('recusa %j', (name) => {
    expect(validateServiceName(name)).toBe(NAME_ERROR);
  });
});

describe('parsePrice', () => {
  it.each([
    ['35', '35.00'],
    ['35,5', '35.50'],
    ['35.5', '35.50'],
    ['35,05', '35.05'],
    [' 40,00 ', '40.00'],
    ['0', '0.00'],
    ['0,99', '0.99'],
    ['007', '7.00'],
    ['99999999,99', '99999999.99'],
  ])('%j vira %j', (text, api) => {
    expect(parsePrice(text)).toBe(api);
    expect(validatePrice(text)).toBeNull();
  });

  it.each([
    '',
    'abc',
    '-1',
    '35,555',
    '1.234,56',
    '35,',
    ',5',
    'R$ 35',
    '100000000',
    '100000000,00',
    '0000000000100000000',
    '1e3',
  ])('recusa %j', (text) => {
    expect(parsePrice(text)).toBeNull();
    expect(validatePrice(text)).toBe(PRICE_ERROR);
  });
});

describe('parseDuration', () => {
  it.each([
    ['1', 1],
    ['30', 30],
    [' 45 ', 45],
    ['720', 720],
  ])('%j vira %d', (text, minutes) => {
    expect(parseDuration(text)).toBe(minutes);
    expect(validateDuration(text)).toBeNull();
  });

  it.each(['', '0', '721', '-5', '30,5', '30.0', 'trinta', '1e2'])('recusa %j', (text) => {
    expect(parseDuration(text)).toBeNull();
    expect(validateDuration(text)).toBe(DURATION_ERROR);
  });
});

describe('formatação do preço', () => {
  it('priceToInput mostra com vírgula e 2 casas', () => {
    expect(priceToInput('35.00')).toBe('35,00');
    expect(priceToInput(40.5)).toBe('40,50');
  });

  it('formatPrice mostra em reais', () => {
    // O Intl separa "R$" do valor com um espaço inseparável.
    expect(formatPrice('35.5').replace(/\s/g, ' ')).toBe('R$ 35,50');
    expect(formatPrice('1234').replace(/\s/g, ' ')).toBe('R$ 1.234,00');
  });
});
