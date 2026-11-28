import { describe, expect, it } from 'vitest';
import { addDays, formatIsoDate, formatLongDate, formatShopDate, formatShopDateTime, shopToday, toStartDatetime } from './shopDate';

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

describe('formatShopDateTime', () => {
  it('mostra o horário UTC da API no fuso da barbearia (SPEC/2026-11-25-meus-agendamentos.md)', () => {
    expect(formatShopDateTime('2026-12-02T13:00:00Z')).toBe('qua., 02/12/2026 às 10:00');
  });

  it('às 23h30 de Brasília ainda é o mesmo dia, embora em UTC já seja o seguinte', () => {
    expect(formatShopDateTime('2026-12-03T02:30:00Z')).toBe('qua., 02/12/2026 às 23:30');
  });

  it('entende o horário com fuso e aceita outro fuso', () => {
    expect(formatShopDateTime('2026-12-02T10:00:00-03:00')).toBe('qua., 02/12/2026 às 10:00');
    expect(formatShopDateTime('2026-12-02T13:00:00Z', 'UTC')).toBe('qua., 02/12/2026 às 13:00');
  });
});

describe('formatShopDate', () => {
  it('mostra o dia no fuso da barbearia (SPEC/2026-11-26-painel-galeria.md)', () => {
    expect(formatShopDate('2026-11-26T12:00:00Z')).toBe('26/11/2026');
  });

  it('à 1h UTC ainda é o dia anterior em Brasília', () => {
    expect(formatShopDate('2026-11-27T01:00:00Z')).toBe('26/11/2026');
  });
});

describe('formatIsoDate', () => {
  it('mostra a data da API como dia/mês/ano, sem passar pelo fuso (SPEC/2026-11-26-painel-trim-club.md)', () => {
    expect(formatIsoDate('2026-12-26')).toBe('26/12/2026');
    expect(formatIsoDate('2027-01-01')).toBe('01/01/2027');
  });
});
