import { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import ConfirmButton from '../ConfirmButton';
import type { NamedItem } from '../../hooks/useNameList';

// Uma linha da lista de nomes (NameList): "Renomear" troca o nome pelo campo na própria linha;
// "Excluir" pede confirmação.

type Props<T extends NamedItem> = {
  item: T;
  busy: boolean;
  /** Pergunta da confirmação da exclusão. */
  deleteQuestion: string;
  /** Grava o nome novo. Devolve true quando gravou, para a linha sair da edição. */
  onRename: (item: T, name: string) => Promise<boolean>;
  onDelete: (item: T) => void;
};

const NameRow = <T extends NamedItem>({ item, busy, deleteQuestion, onRename, onDelete }: Props<T>) => {
  // null: fora da edição.
  const [name, setName] = useState<string | null>(null);

  const save = async () => {
    if (name !== null && (await onRename(item, name))) setName(null);
  };

  if (name !== null) {
    return (
      <tr aria-label={item.name}>
        <td>
          <input aria-label={`Novo nome de ${item.name}`} value={name} onChange={(e) => setName(e.target.value)} />
        </td>
        <td>
          <button className={shared.btnIcon} onClick={save} disabled={busy}>Salvar</button>
          <button className={shared.btnIcon} onClick={() => setName(null)} disabled={busy}>Cancelar</button>
        </td>
      </tr>
    );
  }

  return (
    <tr aria-label={item.name}>
      <td style={{ color: '#fff', fontWeight: 500 }}>{item.name}</td>
      <td>
        <ConfirmButton label="Excluir" question={deleteQuestion} onConfirm={() => onDelete(item)} busy={busy}>
          <button className={shared.btnIcon} onClick={() => setName(item.name)} disabled={busy}>
            Renomear
          </button>
        </ConfirmButton>
      </td>
    </tr>
  );
};

export default NameRow;
