import type { ExpenseCategory, useExpenseCategories } from '../../hooks/useAdminExpenses';
import { validateCategoryName } from '../../utils/expenseValidation';
import NameList from '../names/NameList';

// Gestão das categorias de despesa, na tela de despesas (SPEC/2026-11-26-painel-despesas.md):
// criar, renomear e excluir, com a lista de nomes genérica (NameList).

type Props = {
  resource: ReturnType<typeof useExpenseCategories>;
  /** A categoria foi renomeada (com o nome novo) ou excluída (null): a lista de despesas acompanha. */
  onChanged: (id: string, category: ExpenseCategory | null) => void;
};

const ExpenseCategories = ({ resource, onChanged }: Props) => (
  <NameList
    resource={resource}
    title="Categorias"
    noun="Categoria"
    deleteQuestion="Excluir a categoria? As despesas ficam sem categoria."
    validate={validateCategoryName}
    onChanged={onChanged}
  />
);

export default ExpenseCategories;
