import { describe, expect, it } from 'vitest';
import { canFinish } from './appointmentStatus';

const now = new Date('2026-11-08T17:00:00Z'); // 14:00 em Brasília

describe('canFinish', () => {
  it('libera agendamento confirmado ou pendente que já começou', () => {
    expect(canFinish({ status: 'confirmed', start_datetime: '2026-11-08T16:30:00Z' }, now)).toBe(true);
    expect(canFinish({ status: 'pending', start_datetime: '2026-11-08T17:00:00Z' }, now)).toBe(true);
  });

  it('não libera agendamento que ainda não começou', () => {
    expect(canFinish({ status: 'confirmed', start_datetime: '2026-11-08T17:30:00Z' }, now)).toBe(false);
  });

  it.each(['completed', 'cancelled', 'no_show'])('não libera status final %s', (status) => {
    expect(canFinish({ status, start_datetime: '2026-11-08T16:30:00Z' }, now)).toBe(false);
  });

  it('entende o horário com fuso que a API devolve', () => {
    expect(canFinish({ status: 'confirmed', start_datetime: '2026-11-08T13:30:00-03:00' }, now)).toBe(true);
    expect(canFinish({ status: 'confirmed', start_datetime: '2026-11-08T14:30:00-03:00' }, now)).toBe(false);
  });
});
