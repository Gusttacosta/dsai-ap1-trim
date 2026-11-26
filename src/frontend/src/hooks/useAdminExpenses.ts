import { useCallback } from 'react';
import api from '../api';
import { useApiResource } from './useApiResource';
import { upsert, useNameList } from './useNameList';

// Despesas e categorias do painel do admin (SPEC/2026-11-26-painel-despesas.md), sobre as rotas
// de /expenses (SPEC/2026-11-25-despesas-validacoes.md). As ações devolvem o que o backend
// gravou e lançam o erro da API, para quem chamou mostrar a mensagem.

export type ExpenseCategory = { id: string; name: string; created_at: string };

export type Expense = {
  id: string;
  category_id: string | null;
  description: string;
  /** O backend serializa o Decimal como texto, com 2 casas ("100.50"). */
  amount: string;
  /** "AAAA-MM-DD" */
  payment_date: string;
  is_recurring: boolean;
  created_at: string;
  updated_at: string;
  category: ExpenseCategory | null;
};

/** Campos da criação, já no formato da API. */
export type ExpenseInput = Pick<Expense, 'category_id' | 'description' | 'amount' | 'payment_date' | 'is_recurring'>;
/** Alteração parcial: só os campos que mudaram. */
export type ExpenseChanges = Partial<ExpenseInput>;

/** Período da lista, em "AAAA-MM-DD". Vazio não filtra. */
export type Period = { start: string; end: string };

/** Mesma ordem do backend: data do pagamento mais recente primeiro. */
const byDateDesc = (a: Expense, b: Expense) => b.payment_date.localeCompare(a.payment_date);

/** Categorias de despesa: `items`, `create`, `rename` e `remove` (useNameList). */
export const useExpenseCategories = () =>
  useNameList<ExpenseCategory>('/expenses/categories', 'Não foi possível carregar as categorias.');

export function useAdminExpenses({ start, end }: Period) {
  const load = useCallback(async () => {
    const params: Record<string, string> = {};
    if (start) params.start_date = start;
    if (end) params.end_date = end;
    return (await api.get<Expense[]>('/expenses', { params })).data;
  }, [start, end]);

  const { data: expenses, setData, status, loadError, reload } = useApiResource(
    load,
    [] as Expense[],
    'Não foi possível carregar as despesas.',
  );

  const store = useCallback((saved: Expense) => {
    setData((current) => upsert(current, saved, byDateDesc));
    return saved;
  }, []);

  const createExpense = useCallback(
    async (input: ExpenseInput) => store((await api.post<Expense>('/expenses', input)).data),
    [store],
  );

  const updateExpense = useCallback(
    async (id: string, changes: ExpenseChanges) => store((await api.put<Expense>(`/expenses/${id}`, changes)).data),
    [store],
  );

  const deleteExpense = useCallback(async (id: string) => {
    await api.delete(`/expenses/${id}`);
    setData((current) => current.filter((e) => e.id !== id));
  }, []);

  /**
   * Leva para as despesas da lista a categoria renomeada, ou tira a categoria apagada (`null`):
   * o backend já fez o mesmo (`ON DELETE SET NULL`), e a lista não precisa ser carregada de novo.
   */
  const syncCategory = useCallback((id: string, category: ExpenseCategory | null) => {
    setData((current) =>
      current.map((e) =>
        e.category_id === id ? { ...e, category, category_id: category ? category.id : null } : e,
      ),
    );
  }, []);

  return { expenses, status, loadError, reload, createExpense, updateExpense, deleteExpense, syncCategory };
}
