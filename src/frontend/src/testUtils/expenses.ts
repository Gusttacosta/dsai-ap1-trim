import type { Expense, ExpenseCategory } from '../hooks/useAdminExpenses';

// Despesas e categorias como a API as devolve, para os testes do painel de despesas
// (SPEC/2026-11-26-painel-despesas.md).

export const expenseCategory = (name: string): ExpenseCategory => ({
  id: name.toLowerCase(),
  name,
  created_at: '2026-11-01T10:00:00',
});

export const ALUGUEL = expenseCategory('Aluguel');
export const LUZ = expenseCategory('Luz');

export function makeExpense(id: string, extra: Partial<Expense> = {}, category: ExpenseCategory | null = null): Expense {
  return {
    id,
    category_id: category?.id ?? null,
    description: `Despesa ${id}`,
    amount: '100.00',
    payment_date: '2026-11-20',
    is_recurring: false,
    created_at: '2026-11-01T10:00:00',
    updated_at: '2026-11-01T10:00:00',
    category,
    ...extra,
  };
}
