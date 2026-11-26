// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { barber } from '../testUtils/barbers';
import { httpError } from '../testUtils/httpError';
import {
  syncBarberServices,
  useAdminBarbers,
  useBarberServiceChoices,
} from './useAdminBarbers';
import { useBarberSchedule, type WorkDay } from './useBarberSchedule';

// SPEC/2026-11-26-painel-barbeiros.md: carga e ações dos barbeiros, vínculos e escala.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };


const ANA = barber('ana', 'Ana');
const BRUNO = barber('bruno', 'Bruno', { is_active: false });

async function loaded() {
  mocked.get.mockResolvedValue({ data: [ANA, BRUNO] });
  const hook = renderHook(() => useAdminBarbers());
  await waitFor(() => expect(hook.result.current.status).toBe('ready'));
  return hook;
}

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

describe('useAdminBarbers', () => {
  it('carrega a listagem do admin, com ativos e desativados', async () => {
    const { result } = await loaded();
    expect(mocked.get).toHaveBeenCalledWith('/barbers/admin');
    expect(result.current.barbers).toEqual([ANA, BRUNO]);
  });

  it('falha da carga mostra a mensagem do backend', async () => {
    mocked.get.mockRejectedValue(httpError(403, 'Acesso restrito a administradores.'));
    const { result } = renderHook(() => useAdminBarbers());
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Acesso restrito a administradores.');
  });

  it('criar manda o perfil, devolve o id e carrega a lista de novo', async () => {
    const { result } = await loaded();
    mocked.post.mockResolvedValue({ data: { id: 'novo' } });

    let id = '';
    await act(async () => {
      id = await result.current.createBarber({ user_id: 'u1', commission_rate: '40.00' });
    });

    expect(id).toBe('novo');
    expect(mocked.post).toHaveBeenCalledWith('/barbers', { user_id: 'u1', commission_rate: '40.00' });
    await waitFor(() => expect(mocked.get).toHaveBeenCalledTimes(2));
  });

  it('alterar manda só as mudanças e troca o barbeiro na lista', async () => {
    const { result } = await loaded();
    const saved = { ...ANA, bio: null, commission_rate: '30.00' };
    mocked.put.mockResolvedValue({ data: saved });

    await act(() => result.current.updateBarber('ana', { commission_rate: '30.00', bio: null }));

    expect(mocked.put).toHaveBeenCalledWith('/barbers/ana', { commission_rate: '30.00', bio: null });
    expect(result.current.barbers).toEqual([saved, BRUNO]);
  });

  it('desativar recusado pelo backend lança o erro e não muda a lista', async () => {
    const { result } = await loaded();
    mocked.put.mockRejectedValue(httpError(400, 'O barbeiro tem 2 agendamento(s) futuro(s).'));

    await expect(act(() => result.current.setActive('ana', false))).rejects.toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/barbers/ana', { is_active: false });
    expect(result.current.barbers[0].is_active).toBe(true);
  });
});

describe('serviços do barbeiro', () => {
  it('sincronizar vincula os que faltam e desvincula os que sobram, a partir do que está gravado', async () => {
    mocked.get.mockResolvedValue({ data: [{ id: 'corte' }, { id: 'barba' }] });
    mocked.post.mockResolvedValue({});
    mocked.delete.mockResolvedValue({});

    await syncBarberServices('ana', ['corte', 'luzes']);

    expect(mocked.get).toHaveBeenCalledWith('/services/barber/ana');
    expect(mocked.post.mock.calls).toEqual([['/services/luzes/barbers/ana']]);
    expect(mocked.delete.mock.calls).toEqual([['/services/barba/barbers/ana']]);
  });

  it('a escolha traz só os serviços ativos e os vinculados', async () => {
    mocked.get.mockImplementation(async (url: string) =>
      url === '/services/admin'
        ? { data: [{ id: 'corte', is_active: true }, { id: 'velho', is_active: false }] }
        : { data: [{ id: 'corte' }] },
    );
    const { result } = renderHook(() => useBarberServiceChoices('ana'));
    await waitFor(() => expect(result.current.status).toBe('ready'));

    expect(result.current.data.options.map((s) => s.id)).toEqual(['corte']);
    expect(result.current.data.linkedIds).toEqual(['corte']);
  });

  it('na criação não há vinculados para buscar', async () => {
    mocked.get.mockResolvedValue({ data: [] });
    const { result } = renderHook(() => useBarberServiceChoices(null));
    await waitFor(() => expect(result.current.status).toBe('ready'));
    expect(mocked.get).toHaveBeenCalledTimes(1);
    expect(result.current.data.linkedIds).toEqual([]);
  });
});

describe('useBarberSchedule', () => {
  const MONDAY: WorkDay = {
    id: 'd1',
    day_of_week: 1,
    start_time: '09:00:00',
    end_time: '18:00:00',
    break_start: '12:00:00',
    break_end: '13:00:00',
    is_working: true,
  };

  it('carrega a semana e grava os 7 dias de uma vez', async () => {
    mocked.get.mockResolvedValue({ data: [MONDAY] });
    const { result } = renderHook(() => useBarberSchedule('ana'));
    await waitFor(() => expect(result.current.status).toBe('ready'));
    expect(mocked.get).toHaveBeenCalledWith('/barbers/ana/schedule');

    const saved = { ...MONDAY, break_start: null, break_end: null };
    mocked.put.mockResolvedValue({ data: [saved] });
    const { id: _id, ...input } = saved;
    await act(() => result.current.saveWeek([input]));

    expect(mocked.put).toHaveBeenCalledWith('/barbers/ana/schedule', [input]);
    expect(result.current.week).toEqual([saved]);
  });

  it('falha da gravação lança o erro e mantém a semana', async () => {
    mocked.get.mockResolvedValue({ data: [MONDAY] });
    mocked.put.mockRejectedValue(httpError(422, [{ msg: 'Value error, O almoço deve ficar dentro do expediente.' }]));
    const { result } = renderHook(() => useBarberSchedule('ana'));
    await waitFor(() => expect(result.current.status).toBe('ready'));

    await expect(act(() => result.current.saveWeek([]))).rejects.toBeTruthy();
    expect(result.current.week).toEqual([MONDAY]);
  });
});
