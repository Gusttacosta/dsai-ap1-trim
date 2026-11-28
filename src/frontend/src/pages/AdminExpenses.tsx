import { useState } from 'react';
import styles from './AdminShared.module.css';
import LoadState, { ActionFeedback } from '../components/LoadState';
import ExpenseCategories from '../components/expenses/ExpenseCategories';
import ExpenseFilters, { ALL, filterByCategory } from '../components/expenses/ExpenseFilters';
import ExpenseForm from '../components/expenses/ExpenseForm';
import ExpenseRow from '../components/expenses/ExpenseRow';
import {
  useAdminExpenses,
  useExpenseCategories,
  type Expense,
  type ExpenseCategory,
  type ExpenseChanges,
  type ExpenseInput,
  type Period,
} from '../hooks/useAdminExpenses';
import { useRowAction } from '../hooks/useRowAction';
import { formatPrice } from '../utils/serviceValidation';

// Despesas e categorias pelo painel do admin (SPEC/2026-11-26-painel-despesas.md).

/** Formulário aberto: nenhum, o de criação ou o de edição de uma despesa. */
type Editing = null | 'new' | Expense;

const AdminExpenses = () => {
  const [period, setPeriod] = useState<Period>({ start: '', end: '' });
  const [categoryFilter, setCategoryFilter] = useState(ALL);
  const { expenses, status, loadError, reload, createExpense, updateExpense, deleteExpense, syncCategory } =
    useAdminExpenses(period);
  const categories = useExpenseCategories();
  const [editing, setEditing] = useState<Editing>(null);
  const { busyId, message, actionError, run, clear, setMessage } = useRowAction();

  const open = (target: Editing) => {
    clear();
    setEditing(target);
  };

  const save = async (data: ExpenseInput | ExpenseChanges) => {
    if (editing === 'new') {
      await createExpense(data as ExpenseInput);
      setMessage('Despesa lançada.');
    } else if (editing) {
      await updateExpense(editing.id, data);
      setMessage('Despesa atualizada.');
    }
    setEditing(null);
  };

  const categoryChanged = (id: string, category: ExpenseCategory | null) => {
    syncCategory(id, category);
    if (!category && categoryFilter === id) setCategoryFilter(ALL);
  };

  const visible = filterByCategory(expenses, categoryFilter);
  const total = visible.reduce((sum, e) => sum + Number(e.amount), 0);

  const content =
    visible.length === 0 ? (
      <p>Nenhuma despesa no período.</p>
    ) : (
      <>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Data</th>
              <th>Descrição</th>
              <th>Categoria</th>
              <th>Valor</th>
              <th>Recorrente</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((expense) => (
              <ExpenseRow
                key={expense.id}
                expense={expense}
                busy={busyId === expense.id}
                onEdit={open}
                onDelete={(e) => run(e.id, () => deleteExpense(e.id), 'Despesa excluída.')}
              />
            ))}
          </tbody>
        </table>
        <p className={styles.pagination} role="status" aria-label="Total">
          Total: <strong>{formatPrice(total)}</strong>
        </p>
      </>
    );

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>💸 Despesas</h2>
        <button className={styles.btnAction} onClick={() => open('new')} disabled={categories.status === 'loading'}>
          + Nova Despesa
        </button>
      </div>

      {editing && (
        <ExpenseForm
          // Trocar de despesa recria o formulário com os dados da nova.
          key={editing === 'new' ? 'new' : editing.id}
          expense={editing === 'new' ? undefined : editing}
          categories={categories.items}
          onSave={save}
          onCancel={() => setEditing(null)}
        />
      )}

      <ActionFeedback message={message} error={actionError} />

      <ExpenseFilters
        period={period}
        onPeriod={setPeriod}
        category={categoryFilter}
        onCategory={setCategoryFilter}
        categories={categories.items}
      />

      <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando despesas...">
        {content}
      </LoadState>

      <ExpenseCategories resource={categories} onChanged={categoryChanged} />
    </div>
  );
};

export default AdminExpenses;
