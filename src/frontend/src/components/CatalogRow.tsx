import type { ReactNode } from 'react';
import shared from '../pages/AdminShared.module.css';
import ConfirmButton from './ConfirmButton';
import styles from './services/Services.module.css';

// Uma linha de catálogo do painel: o nome com a descrição, as colunas de quem usa, "Editar" e uma
// ação confirmada na própria linha ("Excluir", "Desativar"). Usada pelos planos do Trim Club
// (SPEC/2026-11-26-painel-trim-club.md) e pelos prêmios da fidelidade
// (SPEC/2026-11-26-painel-fidelidade.md).

type Props = {
  name: string;
  description: string | null;
  /** Texto do botão da ação confirmada. */
  actionLabel: string;
  /** Pergunta da confirmação. */
  question: string;
  /** Uma ação desta linha está em andamento: os botões ficam desabilitados. */
  busy: boolean;
  onEdit: () => void;
  onConfirm: () => void;
  /** As colunas entre o nome e as ações. */
  children: ReactNode;
};

const CatalogRow = ({ name, description, actionLabel, question, busy, onEdit, onConfirm, children }: Props) => (
  <tr aria-label={name}>
    <td style={{ color: '#fff', fontWeight: 500 }}>
      {name}
      {description && <span className={styles.description}>{description}</span>}
    </td>
    {children}
    <td>
      <ConfirmButton label={actionLabel} question={question} onConfirm={onConfirm} busy={busy}>
        <button className={shared.btnIcon} onClick={onEdit} disabled={busy}>
          Editar
        </button>
      </ConfirmButton>
    </td>
  </tr>
);

export default CatalogRow;
