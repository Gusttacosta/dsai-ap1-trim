import { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import ConfirmButton from '../ConfirmButton';
import type { ExpenseCategory } from '../../hooks/useAdminExpenses';

// Uma linha da lista de categorias de despesa (SPEC/2026-11-26-painel-despesas.md): "Renomear"
// troca o nome pelo campo na própria linha; "Excluir" pede confirmação.

type Props = {
  category: ExpenseCategory;
  busy: boolean;
  /** Grava o nome novo. Devolve true quando gravou, para a linha sair da edição. */
  onRename: (category: ExpenseCategory, name: string) => Promise<boolean>;
  onDelete: (category: ExpenseCategory) => void;
};

const CategoryRow = ({ category, busy, onRename, onDelete }: Props) => {
  // null: fora da edição.
  const [name, setName] = useState<string | null>(null);

  const save = async () => {
    if (name !== null && (await onRename(category, name))) setName(null);
  };

  if (name !== null) {
    return (
      <tr aria-label={category.name}>
        <td>
          <input aria-label={`Novo nome de ${category.name}`} value={name} onChange={(e) => setName(e.target.value)} />
        </td>
        <td>
          <button className={shared.btnIcon} onClick={save} disabled={busy}>Salvar</button>
          <button className={shared.btnIcon} onClick={() => setName(null)} disabled={busy}>Cancelar</button>
        </td>
      </tr>
    );
  }

  return (
    <tr aria-label={category.name}>
      <td style={{ color: '#fff', fontWeight: 500 }}>{category.name}</td>
      <td>
        <ConfirmButton
          label="Excluir"
          question="Excluir a categoria? As despesas ficam sem categoria."
          onConfirm={() => onDelete(category)}
          busy={busy}
        >
          <button className={shared.btnIcon} onClick={() => setName(category.name)} disabled={busy}>
            Renomear
          </button>
        </ConfirmButton>
      </td>
    </tr>
  );
};

export default CategoryRow;
