import { describe, expect, it } from 'vitest';
import {
  BIO_ERROR,
  BIO_MAX,
  BREAK_INVERTED,
  BREAK_OUTSIDE,
  COMMISSION_ERROR,
  END_BEFORE_START,
  INCOMPLETE_BREAK,
  INSTAGRAM_ERROR,
  parseCommission,
  validateBio,
  validateCommission,
  validateDay,
  validateInstagram,
  validateWeek,
  type DayFields,
} from './barberValidation';

// SPEC/2026-11-26-painel-barbeiros.md: as regras do backend conferidas antes da API.

describe('comissão', () => {
  it.each([
    ['0', '0.00'],
    ['100', '100.00'],
    ['12,5', '12.50'],
    ['33.33', '33.33'],
  ])('%s vira %s', (text, value) => {
    expect(parseCommission(text)).toBe(value);
    expect(validateCommission(text)).toBeNull();
  });

  it.each(['', '-1', '100,01', '101', '12,345', 'abc'])('"%s" é recusado', (text) => {
    expect(parseCommission(text)).toBeNull();
    expect(validateCommission(text)).toBe(COMMISSION_ERROR);
  });
});

describe('bio e Instagram', () => {
  it('a bio aceita até 500 caracteres', () => {
    expect(validateBio('a'.repeat(BIO_MAX))).toBeNull();
    expect(validateBio('a'.repeat(BIO_MAX + 1))).toBe(BIO_ERROR);
  });

  it.each(['', 'https://instagram.com/ana', 'http://instagram.com/ana'])('Instagram "%s" serve', (url) => {
    expect(validateInstagram(url)).toBeNull();
  });

  it.each(['@ana', 'instagram.com/ana', 'https://', 'ftp://x.com'])('Instagram "%s" é recusado', (url) => {
    expect(validateInstagram(url)).toBe(INSTAGRAM_ERROR);
  });
});

const day = (extra: Partial<DayFields> = {}): DayFields => ({
  day_of_week: 2,
  is_working: true,
  start_time: '09:00',
  end_time: '18:00',
  break_start: '12:00',
  break_end: '13:00',
  ...extra,
});

describe('escala', () => {
  it('aceita o dia com e sem almoço, e o almoço encostado no expediente', () => {
    expect(validateDay(day())).toBeNull();
    expect(validateDay(day({ break_start: '', break_end: '' }))).toBeNull();
    expect(validateDay(day({ break_start: '09:00', break_end: '18:00' }))).toBeNull();
  });

  it.each([
    [{ end_time: '09:00' }, END_BEFORE_START],
    [{ end_time: '08:00' }, END_BEFORE_START],
    [{ start_time: '' }, END_BEFORE_START],
    [{ break_end: '' }, INCOMPLETE_BREAK],
    [{ break_start: '' }, INCOMPLETE_BREAK],
    [{ break_start: '13:00', break_end: '12:00' }, BREAK_INVERTED],
    [{ break_start: '12:00', break_end: '12:00' }, BREAK_INVERTED],
    [{ end_time: '12:00', break_start: '14:00', break_end: '15:00' }, BREAK_OUTSIDE],
    [{ break_start: '08:30', break_end: '09:30' }, BREAK_OUTSIDE],
  ])('%o é recusado', (extra, message) => {
    expect(validateDay(day(extra))).toBe(message);
  });

  it('a semana diz o primeiro dia com problema', () => {
    const week = [day({ day_of_week: 0 }), day({ day_of_week: 2, break_end: '' }), day({ day_of_week: 3, end_time: '08:00' })];
    expect(validateWeek(week)).toBe(`Terça: ${INCOMPLETE_BREAK}`);
    expect(validateWeek([day({ day_of_week: 0 })])).toBeNull();
  });
});
