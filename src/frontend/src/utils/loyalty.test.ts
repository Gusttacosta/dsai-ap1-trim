import { describe, expect, it } from 'vitest';
import {
  ADJUST_POINTS_ERROR,
  ADJUST_REASON_ERROR,
  POINTS_COST_ERROR,
  REWARD_DESCRIPTION_ERROR,
  REWARD_NAME_ERROR,
  formatPoints,
  parsePoints,
  validateAdjustPoints,
  validateAdjustReason,
  validatePointsCost,
  validateRewardDescription,
  validateRewardName,
} from './loyalty';

// SPEC/2026-11-26-painel-fidelidade.md: as regras do backend conferidas na tela.

describe('parsePoints', () => {
  it.each([
    ['1', 1],
    [' 120 ', 120],
    ['1000000', 1_000_000],
  ])('aceita %j', (text, points) => {
    expect(parsePoints(text)).toBe(points);
  });

  it.each(['', '0', '-5', '1,5', '1.5', 'dez', '1000001', '1 000'])('recusa %j', (text) => {
    expect(parsePoints(text)).toBeNull();
  });
});

describe('formatPoints', () => {
  it('separa o milhar', () => {
    expect(formatPoints(1200)).toBe('1.200 pts');
    expect(formatPoints(0)).toBe('0 pts');
  });
});

describe('prêmio', () => {
  it('o nome tem de 1 a 150 caracteres, sem os espaços das pontas', () => {
    expect(validateRewardName(' Pomada ')).toBeNull();
    expect(validateRewardName('x'.repeat(150))).toBeNull();
    expect(validateRewardName('   ')).toBe(REWARD_NAME_ERROR);
    expect(validateRewardName('x'.repeat(151))).toBe(REWARD_NAME_ERROR);
  });

  it('a descrição é opcional, até 500 caracteres', () => {
    expect(validateRewardDescription('')).toBeNull();
    expect(validateRewardDescription('x'.repeat(500))).toBeNull();
    expect(validateRewardDescription('x'.repeat(501))).toBe(REWARD_DESCRIPTION_ERROR);
  });

  it('o custo é um inteiro de pontos maior que zero', () => {
    expect(validatePointsCost('120')).toBeNull();
    expect(validatePointsCost('0')).toBe(POINTS_COST_ERROR);
    expect(validatePointsCost('12,5')).toBe(POINTS_COST_ERROR);
  });
});

describe('ajuste de pontos', () => {
  it('os pontos são um inteiro de 1 a 1.000.000', () => {
    expect(validateAdjustPoints('50')).toBeNull();
    expect(validateAdjustPoints('')).toBe(ADJUST_POINTS_ERROR);
    expect(validateAdjustPoints('1000001')).toBe(ADJUST_POINTS_ERROR);
  });

  it('o motivo tem de 3 a 200 caracteres, sem os espaços das pontas', () => {
    expect(validateAdjustReason('  abc  ')).toBeNull();
    expect(validateAdjustReason('x'.repeat(200))).toBeNull();
    expect(validateAdjustReason('')).toBe(ADJUST_REASON_ERROR);
    expect(validateAdjustReason('  ab  ')).toBe(ADJUST_REASON_ERROR);
    expect(validateAdjustReason('x'.repeat(201))).toBe(ADJUST_REASON_ERROR);
  });
});
