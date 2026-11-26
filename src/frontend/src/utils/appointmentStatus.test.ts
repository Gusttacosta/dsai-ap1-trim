import { describe, expect, it } from 'vitest';
import { canCancel, canFinish, splitByStart, STATUS_LABELS } from './appointmentStatus';

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

// SPEC/2026-11-25-meus-agendamentos.md: a regra de cancelar é a de cancel_by_client no backend.
describe('canCancel', () => {
  it('libera agendamento pendente ou confirmado que ainda não começou', () => {
    expect(canCancel({ status: 'confirmed', start_datetime: '2026-11-08T17:30:00Z' }, now)).toBe(true);
    expect(canCancel({ status: 'pending', start_datetime: '2026-11-09T12:00:00Z' }, now)).toBe(true);
  });

  it('não libera agendamento que já começou, nem no minuto exato do início', () => {
    expect(canCancel({ status: 'confirmed', start_datetime: '2026-11-08T17:00:00Z' }, now)).toBe(false);
    expect(canCancel({ status: 'pending', start_datetime: '2026-11-08T16:30:00Z' }, now)).toBe(false);
  });

  it.each(['completed', 'cancelled', 'no_show'])('não libera status final %s, mesmo no futuro', (status) => {
    expect(canCancel({ status, start_datetime: '2026-11-09T12:00:00Z' }, now)).toBe(false);
  });

  it('entende o horário com fuso que a API devolve', () => {
    expect(canCancel({ status: 'confirmed', start_datetime: '2026-11-08T14:30:00-03:00' }, now)).toBe(true);
    expect(canCancel({ status: 'confirmed', start_datetime: '2026-11-08T13:30:00-03:00' }, now)).toBe(false);
  });
});

describe('splitByStart', () => {
  const at = (id: string, start_datetime: string) => ({ id, status: 'confirmed', start_datetime });

  it('separa próximos (do mais próximo ao mais distante) e anteriores (do mais recente ao mais antigo)', () => {
    const list = [
      at('passado-antigo', '2026-11-01T12:00:00Z'),
      at('futuro-longe', '2026-11-20T12:00:00Z'),
      at('agora', '2026-11-08T17:00:00Z'),
      at('futuro-perto', '2026-11-09T12:00:00Z'),
      at('passado-recente', '2026-11-07T12:00:00Z'),
    ];

    const { upcoming, past } = splitByStart(list, now);

    expect(upcoming.map((a) => a.id)).toEqual(['futuro-perto', 'futuro-longe']);
    expect(past.map((a) => a.id)).toEqual(['agora', 'passado-recente', 'passado-antigo']);
  });

  it('não altera a lista recebida', () => {
    const list = [at('b', '2026-11-20T12:00:00Z'), at('a', '2026-11-09T12:00:00Z')];
    splitByStart(list, now);
    expect(list.map((a) => a.id)).toEqual(['b', 'a']);
  });
});

describe('STATUS_LABELS', () => {
  it('tem os cinco status do backend em português', () => {
    expect(STATUS_LABELS).toEqual({
      pending: 'Pendente',
      confirmed: 'Confirmado',
      completed: 'Concluído',
      cancelled: 'Cancelado',
      no_show: 'Não compareceu',
    });
  });
});
