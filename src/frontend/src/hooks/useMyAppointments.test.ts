// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { httpError, networkError } from '../testUtils/httpError';
import { useMyAppointments, type MyAppointment } from './useMyAppointments';

// SPEC/2026-11-25-meus-agendamentos.md: carga pelo GET /appointments/me, nomes dos barbeiros
// pelo GET /barbers e cancelamento pelo PUT /appointments/{id}/cancel.

vi.mock('../api', () => ({ default: { get: vi.fn(), put: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; put: Mock };

const appointment = (id: string, extra: Partial<MyAppointment> = {}): MyAppointment => ({
  id,
  barber_id: 'b1',
  start_datetime: '2026-12-02T13:00:00Z',
  end_datetime: '2026-12-02T13:30:00Z',
  status: 'confirmed',
  total_price: '40.00',
  items: [{ id: `${id}-i`, service_name: 'Corte', locked_price: '40.00', duration_minutes: 30 }],
  ...extra,
});

const A1 = appointment('a1');
const A2 = appointment('a2', { status: 'completed' });
const BARBERS = [{ id: 'b1', full_name: 'João' }];

/** Responde cada GET pela rota, como o backend. */
function routes(byUrl: Record<string, () => Promise<unknown>>) {
  mocked.get.mockImplementation((url: string) => byUrl[url]());
}

async function loaded() {
  routes({
    '/appointments/me': async () => ({ data: [A1, A2] }),
    '/barbers': async () => ({ data: BARBERS }),
  });
  const hook = renderHook(() => useMyAppointments());
  await waitFor(() => expect(hook.result.current.status).toBe('ready'));
  return hook;
}

beforeEach(() => {
  mocked.get.mockReset();
  mocked.put.mockReset();
});

describe('useMyAppointments: carga', () => {
  it('carrega os agendamentos do cliente e o nome dos barbeiros', async () => {
    const { result } = await loaded();

    expect(mocked.get).toHaveBeenCalledWith('/appointments/me');
    expect(mocked.get).toHaveBeenCalledWith('/barbers');
    expect(result.current.appointments).toEqual([A1, A2]);
    expect(result.current.barberNames).toEqual({ b1: 'João' });
  });

  it('começa carregando', () => {
    mocked.get.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useMyAppointments());

    expect(result.current.status).toBe('loading');
  });

  it('sem a vitrine de barbeiros, os agendamentos aparecem do mesmo jeito', async () => {
    routes({
      '/appointments/me': async () => ({ data: [A1] }),
      '/barbers': async () => Promise.reject(networkError()),
    });
    const { result } = renderHook(() => useMyAppointments());

    await waitFor(() => expect(result.current.status).toBe('ready'));
    expect(result.current.appointments).toEqual([A1]);
    expect(result.current.barberNames).toEqual({});
  });

  it('falha na carga mostra a mensagem do backend', async () => {
    routes({
      '/appointments/me': async () => Promise.reject(httpError(401, 'Token inválido.')),
      '/barbers': async () => ({ data: BARBERS }),
    });
    const { result } = renderHook(() => useMyAppointments());

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Token inválido.');
  });

  it('sem conexão, mostra a mensagem de rede', async () => {
    routes({
      '/appointments/me': async () => Promise.reject(networkError()),
      '/barbers': async () => ({ data: BARBERS }),
    });
    const { result } = renderHook(() => useMyAppointments());

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Sem conexão com o servidor. Verifique a internet e tente de novo.');
  });

  it('"Tentar de novo" carrega outra vez', async () => {
    let calls = 0;
    routes({
      '/appointments/me': async () => (++calls === 1 ? Promise.reject(httpError(500)) : { data: [A1] }),
      '/barbers': async () => ({ data: BARBERS }),
    });
    const { result } = renderHook(() => useMyAppointments());
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Não foi possível carregar seus agendamentos.');

    act(() => result.current.reload());

    await waitFor(() => expect(result.current.status).toBe('ready'));
    expect(result.current.appointments).toEqual([A1]);
  });
});

describe('useMyAppointments: cancelamento', () => {
  it('chama o PUT de cancelamento e troca o agendamento pelo que o backend devolveu', async () => {
    const { result } = await loaded();
    const cancelled = { ...A1, status: 'cancelled' };
    mocked.put.mockResolvedValue({ data: cancelled });

    let returned: MyAppointment | undefined;
    await act(async () => {
      returned = await result.current.cancelAppointment('a1');
    });

    expect(mocked.put).toHaveBeenCalledWith('/appointments/a1/cancel');
    expect(returned).toEqual(cancelled);
    expect(result.current.appointments).toEqual([cancelled, A2]);
  });

  it.each([
    [400, 'Não é possível cancelar um agendamento que já começou.'],
    [404, 'Agendamento não encontrado.'],
  ])('erro %i: lança o erro e mantém a lista', async (code, detail) => {
    const { result } = await loaded();
    mocked.put.mockRejectedValue(httpError(code, detail));

    await act(async () => {
      await expect(result.current.cancelAppointment('a1')).rejects.toMatchObject({
        response: { status: code, data: { detail } },
      });
    });

    expect(result.current.appointments).toEqual([A1, A2]);
  });
});
