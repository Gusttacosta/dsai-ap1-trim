// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { ALUGUEL, LUZ, expenseCategory, makeExpense } from '../testUtils/expenses';
import { httpError } from '../testUtils/httpError';
import {
  useAdminExpenses,
  useExpenseCategories,
  type Expense,
  type ExpenseCategory,
  type Period,
} from './useAdminExpenses';

// SPEC/2026-11-26-painel-despesas.md: carga e ações das despesas e das categorias.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

const E1 = makeExpense('e1', {}, ALUGUEL);
const E2 = makeExpense('e2', { payment_date: '2026-11-10' }, LUZ);
const expense = (id: string, payment_date: string) => makeExpense(id, { payment_date });
const category = expenseCategory;

const NO_PERIOD: Period = { start: '', end: '' };

async function loadedExpenses(list: Expense[] = [E1, E2], period: Period = NO_PERIOD) {
  mocked.get.mockResolvedValue({ data: list });
  const hook = renderHook((p: Period) => useAdminExpenses(p), { initialProps: period });
  await waitFor(() => expect(hook.result.current.status).toBe('ready'));
  return hook;
}

async function loadedCategories(list: ExpenseCategory[] = [ALUGUEL, LUZ]) {
  mocked.get.mockResolvedValue({ data: list });
  const hook = renderHook(() => useExpenseCategories());
  await waitFor(() => expect(hook.result.current.status).toBe('ready'));
  return hook;
}

const ids = (list: { id: string }[]) => list.map((item) => item.id);

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

describe('useAdminExpenses: carga', () => {
  it('sem período, não manda filtro', async () => {
    const { result } = await loadedExpenses();

    expect(mocked.get).toHaveBeenCalledWith('/expenses', { params: {} });
    expect(result.current.expenses).toEqual([E1, E2]);
  });

  it('manda o período como start_date e end_date, e carrega de novo quando ele muda', async () => {
    const { rerender } = await loadedExpenses([E1], { start: '2026-11-01', end: '' });
    expect(mocked.get).toHaveBeenLastCalledWith('/expenses', { params: { start_date: '2026-11-01' } });

    rerender({ start: '2026-11-01', end: '2026-11-30' });

    await waitFor(() =>
      expect(mocked.get).toHaveBeenLastCalledWith('/expenses', {
        params: { start_date: '2026-11-01', end_date: '2026-11-30' },
      }),
    );
  });

  it('o 422 do período invertido vira o erro da carga', async () => {
    mocked.get.mockRejectedValue(httpError(422, 'A data inicial não pode ser depois da data final.'));
    const { result } = renderHook(() => useAdminExpenses({ start: '2026-11-30', end: '2026-11-01' }));

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('A data inicial não pode ser depois da data final.');
  });

  it('falha sem mensagem usa o texto padrão', async () => {
    mocked.get.mockRejectedValue(httpError(500));
    const { result } = renderHook(() => useAdminExpenses(NO_PERIOD));

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Não foi possível carregar as despesas.');
  });
});

describe('useAdminExpenses: ações', () => {
  it('criar manda os campos e põe a despesa na lista, pela data', async () => {
    const { result } = await loadedExpenses();
    const created = expense('e3', '2026-11-15');
    mocked.post.mockResolvedValue({ data: created });
    const input = { category_id: null, description: 'Água', amount: '50.00', payment_date: '2026-11-15', is_recurring: true };

    await act(() => result.current.createExpense(input));

    expect(mocked.post).toHaveBeenCalledWith('/expenses', input);
    expect(ids(result.current.expenses)).toEqual(['e1', 'e3', 'e2']);
  });

  it('alterar manda só as mudanças e troca a despesa na lista', async () => {
    const { result } = await loadedExpenses();
    const updated = { ...E2, payment_date: '2026-11-25' };
    mocked.put.mockResolvedValue({ data: updated });

    await act(() => result.current.updateExpense('e2', { payment_date: '2026-11-25' }));

    expect(mocked.put).toHaveBeenCalledWith('/expenses/e2', { payment_date: '2026-11-25' });
    expect(result.current.expenses).toEqual([updated, E1]);
  });

  it('excluir chama o DELETE e tira a despesa', async () => {
    const { result } = await loadedExpenses();
    mocked.delete.mockResolvedValue({});

    await act(() => result.current.deleteExpense('e1'));

    expect(mocked.delete).toHaveBeenCalledWith('/expenses/e1');
    expect(ids(result.current.expenses)).toEqual(['e2']);
  });

  it('a falha da API é lançada e a lista não muda', async () => {
    const { result } = await loadedExpenses();
    mocked.delete.mockRejectedValue(httpError(404, 'Despesa não encontrada.'));

    await expect(act(() => result.current.deleteExpense('e1'))).rejects.toThrow();
    expect(ids(result.current.expenses)).toEqual(['e1', 'e2']);
  });

  it('syncCategory leva o novo nome e tira a categoria apagada', async () => {
    const { result } = await loadedExpenses();
    const renamed = { ...ALUGUEL, name: 'Aluguel da loja' };

    act(() => result.current.syncCategory('aluguel', renamed));
    expect(result.current.expenses[0].category).toEqual(renamed);

    act(() => result.current.syncCategory('luz', null));
    expect(result.current.expenses[1]).toMatchObject({ category: null, category_id: null });
    expect(result.current.expenses[0].category_id).toBe('aluguel');
  });
});

describe('useExpenseCategories', () => {
  it('carrega as categorias', async () => {
    const { result } = await loadedCategories();

    expect(mocked.get).toHaveBeenCalledWith('/expenses/categories');
    expect(result.current.items).toEqual([ALUGUEL, LUZ]);
  });

  it('falha na carga mostra a mensagem', async () => {
    mocked.get.mockRejectedValue(httpError(403, 'Acesso restrito a administradores.'));
    const { result } = renderHook(() => useExpenseCategories());

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Acesso restrito a administradores.');
  });

  it('criar põe a categoria em ordem alfabética', async () => {
    const { result } = await loadedCategories();
    const created = category('Internet');
    mocked.post.mockResolvedValue({ data: created });

    await act(() => result.current.create('Internet'));

    expect(mocked.post).toHaveBeenCalledWith('/expenses/categories', { name: 'Internet' });
    expect(result.current.items.map((c) => c.name)).toEqual(['Aluguel', 'Internet', 'Luz']);
  });

  it('renomear chama o PUT e reordena', async () => {
    const { result } = await loadedCategories();
    mocked.put.mockResolvedValue({ data: { ...ALUGUEL, name: 'Templo' } });

    await act(() => result.current.rename('aluguel', 'Templo'));

    expect(mocked.put).toHaveBeenCalledWith('/expenses/categories/aluguel', { name: 'Templo' });
    expect(result.current.items.map((c) => c.name)).toEqual(['Luz', 'Templo']);
  });

  it('nome repetido lança o 400 e a lista não muda', async () => {
    const { result } = await loadedCategories();
    mocked.post.mockRejectedValue(httpError(400, "Já existe uma categoria chamada 'Luz'."));

    await expect(act(() => result.current.create('Luz'))).rejects.toThrow();
    expect(result.current.items).toEqual([ALUGUEL, LUZ]);
  });

  it('excluir chama o DELETE e tira a categoria', async () => {
    const { result } = await loadedCategories();
    mocked.delete.mockResolvedValue({});

    await act(() => result.current.remove('luz'));

    expect(mocked.delete).toHaveBeenCalledWith('/expenses/categories/luz');
    expect(result.current.items).toEqual([ALUGUEL]);
  });
});
