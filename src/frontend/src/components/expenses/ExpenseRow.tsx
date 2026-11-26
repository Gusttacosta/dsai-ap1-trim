import shared from '../../pages/AdminShared.module.css';
import ConfirmButton from '../ConfirmButton';
import type { Expense } from '../../hooks/useAdminExpenses';
import { formatPaymentDate } from '../../utils/expenseValidation';
import { formatPrice } from '../../utils/serviceValidation';

// Uma linha da tabela de despesas do painel (SPEC/2026-11-26-painel-despesas.md).
// "Excluir" pede confirmação na própria linha (ConfirmButton).

type Props = {
  expense: Expense;
  /** Uma ação desta linha está em andamento: os botões ficam desabilitados. */
  busy: boolean;
  onEdit: (expense: Expense) => void;
  onDelete: (expense: Expense) => void;
};

export const NO_CATEGORY = 'Sem categoria';

const ExpenseRow = ({ expense, busy, onEdit, onDelete }: Props) => (
  <tr aria-label={expense.description}>
    <td>{formatPaymentDate(expense.payment_date)}</td>
    <td style={{ color: '#fff', fontWeight: 500 }}>{expense.description}</td>
    <td>{expense.category?.name ?? NO_CATEGORY}</td>
    <td>{formatPrice(expense.amount)}</td>
    <td>{expense.is_recurring ? 'Sim' : 'Não'}</td>
    <td>
      <ConfirmButton label="Excluir" question="Excluir esta despesa?" onConfirm={() => onDelete(expense)} busy={busy}>
        <button className={shared.btnIcon} onClick={() => onEdit(expense)} disabled={busy}>
          Editar
        </button>
      </ConfirmButton>
    </td>
  </tr>
);

export default ExpenseRow;
