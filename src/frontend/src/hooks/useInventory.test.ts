// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { httpError } from '../testUtils/httpError';
import { OLEO, POMADA, SHAMPOO, makeMovement } from '../testUtils/inventory';
import { useAdminProducts, useInventoryHistory } from './useInventory';

// SPEC/2026-11-26-painel-estoque.md: as rotas de /products usadas pelo estoque no painel.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock };

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

async function ready<T extends { status: string }>(hook: () => T) {
  const rendered = renderHook(hook);
  await waitFor(() => expect(rendered.result.current.status).not.toBe('loading'));
  return rendered.result;
}

describe('useAdminProducts', () => {
  it('carrega a lista do admin, e não a vitrine', async () => {
    mocked.get.mockResolvedValue({ data: [OLEO, POMADA] });
    const result = await ready(() => useAdminProducts());
    expect(mocked.get).toHaveBeenCalledWith('/products/admin/all');
    expect(result.current.products.map((p) => p.id)).toEqual(['oleo', 'pomada']);
  });

  it('registra a movimentação e troca a linha pelo produto devolvido', async () => {
    mocked.get.mockResolvedValue({ data: [OLEO, POMADA, SHAMPOO] });
    const result = await ready(() => useAdminProducts());
    mocked.post.mockResolvedValue({ data: { ...POMADA, stock_quantity: 13 } });

    const input = { movement_type: 'restock' as const, quantity: 10, notes: null };
    await act(() => result.current.registerMovement('pomada', input));

    expect(mocked.post).toHaveBeenCalledWith('/products/pomada/inventory', input);
    expect(result.current.products.map((p) => [p.id, p.stock_quantity])).toEqual([
      ['oleo', 0],
      ['pomada', 13],
      ['shampoo', 20],
    ]);
  });

  it('a falha da movimentação lança o erro e o estoque continua', async () => {
    mocked.get.mockResolvedValue({ data: [POMADA] });
    const result = await ready(() => useAdminProducts());
    mocked.post.mockRejectedValue(httpError(400, 'Estoque insuficiente.'));

    await expect(
      act(() => result.current.registerMovement('pomada', { movement_type: 'loss', quantity: -9, notes: null })),
    ).rejects.toThrow();
    expect(result.current.products[0].stock_quantity).toBe(3);
  });

  it('a falha na carga vira a mensagem da API', async () => {
    mocked.get.mockRejectedValue(httpError(403, 'Acesso restrito a administradores.'));
    const result = await ready(() => useAdminProducts());
    expect(result.current.status).toBe('error');
    expect(result.current.loadError).toBe('Acesso restrito a administradores.');
  });
});

describe('useInventoryHistory', () => {
  it('carrega o histórico do produto e recarrega no reload', async () => {
    const movement = makeMovement('m1', POMADA);
    mocked.get.mockResolvedValue({ data: [movement] });
    const result = await ready(() => useInventoryHistory('pomada'));
    expect(mocked.get).toHaveBeenCalledWith('/products/pomada/inventory');
    expect(result.current.movements).toEqual([movement]);

    act(() => result.current.reload());
    await waitFor(() => expect(mocked.get).toHaveBeenCalledTimes(2));
  });

  it('a falha sem mensagem usa a do histórico', async () => {
    mocked.get.mockRejectedValue(httpError(500));
    const result = await ready(() => useInventoryHistory('pomada'));
    expect(result.current.loadError).toBe('Não foi possível carregar o histórico.');
  });
});
