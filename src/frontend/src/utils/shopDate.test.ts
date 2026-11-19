import { describe, expect, it } from 'vitest';
import { addDays, formatLongDate, shopToday, toStartDatetime } from './shopDate';

describe('shopToday', () => {
  it('às 22h de Brasília ainda é o mesmo dia, embora em UTC já seja o seguinte (#12)', () => {
    const lateNight = new Date('2026-11-09T01:00:00Z');

    expect(lateNight.toISOString().slice(0, 10)).toBe('2026-11-09');
    expect(shopToday(lateNight)).toBe('2026-11-08');
  });

  it('à meia-noite de Brasília já é o dia seguinte', () => {
    expect(shopToday(new Date('2026-11-09T03:00:00Z'))).toBe('2026-11-09');
  });

  it('aceita outro fuso', () => {
    expect(shopToday(new Date('2026-11-09T01:00:00Z'), 'UTC')).toBe('2026-11-09');
  });
});

describe('addDays', () => {
  it('atravessa mês e ano', () => {
    expect(addDays('2026-11-08', 30)).toBe('2026-12-08');
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01');
  });
});

describe('formatLongDate', () => {
  it('mostra o dia da semana e a data por extenso', () => {
    expect(formatLongDate('2026-11-09')).toBe('segunda-feira, 09/11/2026');
  });
});

describe('toStartDatetime', () => {
  it('usa a data escolhida, e não a de hoje em UTC', () => {
    expect(toStartDatetime('2026-11-09', '16:30')).toBe('2026-11-09T16:30:00');
  });
});
