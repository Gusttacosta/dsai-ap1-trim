// Datas do agendamento no fuso da barbearia (SPEC/2026-11-18-agendamento-fuso-horario.md).
// Datas são strings "AAAA-MM-DD"; o backend lê horários sem fuso no fuso da barbearia.

export const SHOP_TIMEZONE = 'America/Sao_Paulo';
export const MAX_DAYS_AHEAD = 30;

const parse = (isoDate: string): [number, number, number] => {
  const [year, month, day] = isoDate.split('-').map(Number);
  return [year, month, day];
};

/** "Hoje" no fuso da barbearia, e não em UTC como `toISOString()`. */
export function shopToday(now: Date = new Date(), timeZone: string = SHOP_TIMEZONE): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

export function addDays(isoDate: string, days: number): string {
  const [year, month, day] = parse(isoDate);
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

/** "segunda-feira, 09/11/2026" */
export function formatLongDate(isoDate: string): string {
  const [year, month, day] = parse(isoDate);
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'UTC',
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(Date.UTC(year, month - 1, day, 12)));
}

/** Valor de `start_datetime` enviado à API: sem fuso, lido no fuso da barbearia. */
export function toStartDatetime(isoDate: string, time: string): string {
  return `${isoDate}T${time}:00`;
}

/** Data e hora de um instante da API no fuso da barbearia: "qua., 02/12/2026 às 10:00". */
export function formatShopDateTime(iso: string, timeZone: string = SHOP_TIMEZONE): string {
  const parts = new Intl.DateTimeFormat('pt-BR', {
    timeZone,
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(iso));
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((p) => p.type === type)?.value ?? '';
  return `${part('weekday')}, ${part('day')}/${part('month')}/${part('year')} às ${part('hour')}:${part('minute')}`;
}

/** Dia de um instante da API no fuso da barbearia: "26/11/2026". */
export function formatShopDate(iso: string, timeZone: string = SHOP_TIMEZONE): string {
  return new Intl.DateTimeFormat('pt-BR', { timeZone, day: '2-digit', month: '2-digit', year: 'numeric' }).format(
    new Date(iso),
  );
}
