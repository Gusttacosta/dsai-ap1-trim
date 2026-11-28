// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { httpError, networkError } from '../testUtils/httpError';
import { useAdminServices, type AdminService } from './useAdminServices';

// SPEC/2026-11-23-painel-servicos.md: carga pela listagem do admin e as ações sobre a API.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

const service = (name: string, extra: Partial<AdminService> = {}): AdminService => ({
  id: name.toLowerCase(),
  name,
  description: null,
  price: '30.00',
  duration_minutes: 30,
  is_active: true,
  ...extra,
});

const BARBA = service('Barba');
const CORTE = service('Corte');
const PIGMENTACAO = service('Pigmentação', { is_active: false });

async function loaded(list: AdminService[] = [BARBA, CORTE, PIGMENTACAO]) {
  mocked.get.mockResolvedValue({ data: list });
  const hook = renderHook(() => useAdminServices());
  await waitFor(() => expect(hook.result.current.status).toBe('ready'));
  return hook;
}

const names = (list: AdminService[]) => list.map((s) => s.name);

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

describe('useAdminServices: carga', () => {
  it('usa a listagem do admin, com ativos e desativados', async () => {
    const { result } = await loaded();

    expect(mocked.get).toHaveBeenCalledWith('/services/admin');
    expect(result.current.services).toEqual([BARBA, CORTE, PIGMENTACAO]);
  });

  it('começa carregando', () => {
    mocked.get.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useAdminServices());

    expect(result.current.status).toBe('loading');
  });

  it('falha na carga mostra a mensagem do backend', async () => {
    mocked.get.mockRejectedValue(httpError(403, 'Acesso restrito a administradores.'));
    const { result } = renderHook(() => useAdminServices());

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Acesso restrito a administradores.');
  });

  it('sem conexão, a mensagem diz isso', async () => {
    mocked.get.mockRejectedValue(networkError());
    const { result } = renderHook(() => useAdminServices());

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toMatch(/Sem conexão/);
  });

  it('reload carrega de novo depois de uma falha', async () => {
    mocked.get.mockRejectedValueOnce(httpError(500)).mockResolvedValueOnce({ data: [CORTE] });
    const { result } = renderHook(() => useAdminServices());
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Não foi possível carregar os serviços.');

    act(() => result.current.reload());

    await waitFor(() => expect(result.current.status).toBe('ready'));
    expect(result.current.services).toEqual([CORTE]);
    expect(mocked.get).toHaveBeenCalledTimes(2);
  });
});

describe('useAdminServices: ações', () => {
  it('createService envia o POST e põe o serviço na ordem alfabética', async () => {
    const { result } = await loaded();
    const novo = service('Hidratação');
    mocked.post.mockResolvedValue({ data: novo });
    const input = { name: 'Hidratação', description: null, price: '30.00', duration_minutes: 30 };

    let saved: AdminService | undefined;
    await act(async () => {
      saved = await result.current.createService(input);
    });

    expect(mocked.post).toHaveBeenCalledWith('/services', input);
    expect(saved).toEqual(novo);
    expect(names(result.current.services)).toEqual(['Barba', 'Corte', 'Hidratação', 'Pigmentação']);
  });

  it('a ordem não diferencia maiúsculas nem acentos', async () => {
    const { result } = await loaded([CORTE]);
    mocked.post.mockResolvedValue({ data: service('alisamento') });

    await act(async () => {
      await result.current.createService({ name: 'alisamento', description: null, price: '1.00', duration_minutes: 5 });
    });

    expect(names(result.current.services)).toEqual(['alisamento', 'Corte']);
  });

  it('updateService envia o PUT e troca o serviço na lista, reordenando', async () => {
    const { result } = await loaded();
    const renomeado = { ...BARBA, name: 'Design de barba', price: '40.00' };
    mocked.put.mockResolvedValue({ data: renomeado });

    await act(async () => {
      await result.current.updateService('barba', { name: 'Design de barba', price: '40.00' });
    });

    expect(mocked.put).toHaveBeenCalledWith('/services/barba', { name: 'Design de barba', price: '40.00' });
    expect(result.current.services).toEqual([CORTE, renomeado, PIGMENTACAO]);
  });

  it('deactivateService envia o DELETE e marca o serviço como desativado', async () => {
    const { result } = await loaded();
    mocked.delete.mockResolvedValue({ data: '' });

    await act(async () => {
      await result.current.deactivateService('corte');
    });

    expect(mocked.delete).toHaveBeenCalledWith('/services/corte');
    expect(result.current.services.find((s) => s.id === 'corte')?.is_active).toBe(false);
    expect(result.current.services.find((s) => s.id === 'barba')?.is_active).toBe(true);
  });

  it('reactivateService envia o PUT com is_active true', async () => {
    const { result } = await loaded();
    mocked.put.mockResolvedValue({ data: { ...PIGMENTACAO, is_active: true } });

    await act(async () => {
      await result.current.reactivateService('pigmentação');
    });

    expect(mocked.put).toHaveBeenCalledWith('/services/pigmentação', { is_active: true });
    expect(result.current.services.find((s) => s.name === 'Pigmentação')?.is_active).toBe(true);
  });

  it.each([
    ['createService', 'post', (h: ReturnType<typeof useAdminServices>) =>
      h.createService({ name: 'Corte', description: null, price: '1.00', duration_minutes: 5 })],
    ['updateService', 'put', (h: ReturnType<typeof useAdminServices>) => h.updateService('barba', { name: 'Corte' })],
    ['deactivateService', 'delete', (h: ReturnType<typeof useAdminServices>) => h.deactivateService('barba')],
    ['reactivateService', 'put', (h: ReturnType<typeof useAdminServices>) => h.reactivateService('pigmentação')],
  ] as const)('%s que falha lança o erro e não muda a lista', async (_name, method, action) => {
    const { result } = await loaded();
    const failure = httpError(400, 'Já existe um serviço com esse nome.');
    mocked[method].mockRejectedValue(failure);

    await act(async () => {
      await expect(action(result.current)).rejects.toBe(failure);
    });

    expect(result.current.services).toEqual([BARBA, CORTE, PIGMENTACAO]);
  });
});
