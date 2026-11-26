import shared from '../../pages/AdminShared.module.css';
import type { Expense, ExpenseCategory, Period } from '../../hooks/useAdminExpenses';
import { NO_CATEGORY } from './ExpenseRow';

// Filtros da lista de despesas (SPEC/2026-11-26-painel-despesas.md): o período vai para a API,
// a categoria filtra na tela (a API não tem esse filtro).

/** Valor do filtro de categoria: "" é "Todas"; NONE é "Sem categoria"; o resto é o id. */
export const ALL = '';
export const NONE = '__sem_categoria__';

export function filterByCategory(expenses: Expense[], categoryFilter: string): Expense[] {
  if (categoryFilter === ALL) return expenses;
  const wanted = categoryFilter === NONE ? null : categoryFilter;
  return expenses.filter((e) => e.category_id === wanted);
}

type Props = {
  period: Period;
  onPeriod: (period: Period) => void;
  category: string;
  onCategory: (category: string) => void;
  categories: ExpenseCategory[];
};

const ExpenseFilters = ({ period, onPeriod, category, onCategory, categories }: Props) => (
  <div className={shared.filters}>
    <label>
      De{' '}
      <input type="date" value={period.start} onChange={(e) => onPeriod({ ...period, start: e.target.value })} />
    </label>
    <label>
      Até{' '}
      <input type="date" value={period.end} onChange={(e) => onPeriod({ ...period, end: e.target.value })} />
    </label>
    <label>
      Categoria{' '}
      <select value={category} onChange={(e) => onCategory(e.target.value)}>
        <option value={ALL}>Todas</option>
        {categories.map((c) => (
          <option key={c.id} value={c.id}>{c.name}</option>
        ))}
        <option value={NONE}>{NO_CATEGORY}</option>
      </select>
    </label>
  </div>
);

export default ExpenseFilters;
