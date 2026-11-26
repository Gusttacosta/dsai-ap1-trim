// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { httpError } from '../testUtils/httpError';
import { BASICO, OURO, makePlan, makeSubscription } from '../testUtils/trimClub';
import { useAdminPlans, useMySubscription, useSubscriptions } from './useTrimClub';

// SPEC/2026-11-26-painel-trim-club.md: as rotas de /subscriptions usadas pelo painel e pela conta.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

async function ready<T extends { status: string }>(hook: () => T) {
  const rendered = renderHook(hook);
  await waitFor(() => expect(rendered.result.current.status).not.toBe('loading'));
  return rendered.result;
}

describe('useAdminPlans', () => {
  it('carrega os planos e põe o novo na ordem de preço', async () => {
    mocked.get.mockResolvedValue({ data: [BASICO, OURO] });
    const result = await ready(() => useAdminPlans());
    expect(mocked.get).toHaveBeenCalledWith('/subscriptions/plans');

    const prata = makePlan('prata', { name: 'Prata', monthly_price: '90.00' });
    mocked.post.mockResolvedValue({ data: prata });
    const input = { ...prata, is_active: undefined };
    await act(() => result.current.createPlan(input));

    expect(mocked.post).toHaveBeenCalledWith('/subscriptions/plans', input);
    expect(result.current.plans.map((p) => p.id)).toEqual(['basico', 'prata', 'ouro']);
  });

  it('edita pelo PUT e troca a linha pelo que o backend gravou', async () => {
    mocked.get.mockResolvedValue({ data: [BASICO, OURO] });
    const result = await ready(() => useAdminPlans());
    mocked.put.mockResolvedValue({ data: { ...BASICO, monthly_price: '200.00' } });

    await act(() => result.current.updatePlan('basico', { monthly_price: '200.00' }));

    expect(mocked.put).toHaveBeenCalledWith('/subscriptions/plans/basico', { monthly_price: '200.00' });
    expect(result.current.plans.map((p) => p.id)).toEqual(['ouro', 'basico']);
  });

  it('excluir chama o DELETE e tira o plano; a falha lança e o plano fica', async () => {
    mocked.get.mockResolvedValue({ data: [BASICO, OURO] });
    const result = await ready(() => useAdminPlans());

    mocked.delete.mockRejectedValueOnce(httpError(404, 'Plano não encontrado.'));
    await expect(act(() => result.current.removePlan('ouro'))).rejects.toThrow();
    expect(result.current.plans).toHaveLength(2);

    mocked.delete.mockResolvedValueOnce({ data: null });
    await act(() => result.current.removePlan('ouro'));
    expect(mocked.delete).toHaveBeenCalledWith('/subscriptions/plans/ouro');
    expect(result.current.plans).toEqual([BASICO]);
  });
});

describe('useSubscriptions', () => {
  it('busca o nome de cada assinante uma vez, e a falha de um não impede a lista', async () => {
    const a = makeSubscription('a', { user_id: 'u1' });
    const b = makeSubscription('b', { user_id: 'u2' });
    mocked.get.mockImplementation((url: string) => {
      if (url === '/subscriptions/users') return Promise.resolve({ data: [a, b] });
      if (url === '/auth/users/u1') return Promise.resolve({ data: { full_name: 'Ana', email: 'ana@x.com' } });
      return Promise.reject(httpError(404, 'Usuário não encontrado.'));
    });

    const result = await ready(() => useSubscriptions());

    expect(result.current.status).toBe('ready');
    expect(result.current.subscriptions).toEqual([a, b]);
    expect(result.current.subscribers).toEqual({ u1: { full_name: 'Ana', email: 'ana@x.com' }, u2: null });
  });

  it('o erro da lista vira a mensagem da API', async () => {
    mocked.get.mockRejectedValue(httpError(403, 'Acesso restrito a administradores.'));
    const result = await ready(() => useSubscriptions());
    expect(result.current.status).toBe('error');
    expect(result.current.loadError).toBe('Acesso restrito a administradores.');
  });
});

describe('useMySubscription', () => {
  it('o 404 é "sem assinatura", e não um erro', async () => {
    mocked.get.mockRejectedValue(httpError(404, 'Você não possui uma assinatura.'));
    const result = await ready(() => useMySubscription());
    expect(mocked.get).toHaveBeenCalledWith('/subscriptions/me');
    expect(result.current.status).toBe('ready');
    expect(result.current.subscription).toBeNull();
  });

  it('outro erro mostra a mensagem da API', async () => {
    mocked.get.mockRejectedValue(httpError(500));
    const result = await ready(() => useMySubscription());
    expect(result.current.status).toBe('error');
    expect(result.current.loadError).toBe('Não foi possível carregar sua assinatura.');
  });

  it('cancelar chama o PUT e mostra a assinatura cancelada', async () => {
    mocked.get.mockResolvedValue({ data: makeSubscription('s1') });
    const result = await ready(() => useMySubscription());
    mocked.put.mockResolvedValue({ data: makeSubscription('s1', { status: 'canceled' }) });

    await act(() => result.current.cancel());

    expect(mocked.put).toHaveBeenCalledWith('/subscriptions/me/cancel');
    expect(result.current.subscription?.status).toBe('canceled');
  });
});
