import shared from '../../pages/AdminShared.module.css';
import { StatusBadge } from '../AdminForm';
import ConfirmButton from '../ConfirmButton';
import type { AdminBarber } from '../../hooks/useAdminBarbers';
import { priceToInput } from '../../utils/serviceValidation';
import styles from '../services/Services.module.css';

// Uma linha da tabela de barbeiros do painel (SPEC/2026-11-26-painel-barbeiros.md).
// "Desativar" pede confirmação na própria linha (ConfirmButton). "Reativar" não pede.

type Props = {
  barber: AdminBarber;
  /** Uma ação desta linha está em andamento: os botões ficam desabilitados. */
  busy: boolean;
  onEdit: (barber: AdminBarber) => void;
  onSchedule: (barber: AdminBarber) => void;
  onSetActive: (barber: AdminBarber, isActive: boolean) => void;
};

/** Comissão da API ("50.00") como na tela ("50,00%"). */
export const formatCommission = (rate: string) => `${priceToInput(rate)}%`;

const BarberRow = ({ barber, busy, onEdit, onSchedule, onSetActive }: Props) => {
  const others = (
    <>
      <button className={shared.btnIcon} onClick={() => onEdit(barber)} disabled={busy}>
        Editar
      </button>
      <button className={shared.btnIcon} onClick={() => onSchedule(barber)} disabled={busy}>
        Escala
      </button>
    </>
  );

  return (
    <tr className={barber.is_active ? undefined : styles.inactive} aria-label={barber.full_name}>
      <td style={{ color: '#fff', fontWeight: 500 }}>
        {barber.full_name}
        <span className={styles.description}>{barber.email}</span>
      </td>
      <td>{formatCommission(barber.commission_rate)}</td>
      <td>
        <StatusBadge active={barber.is_active} />
        {!barber.user_is_active && <span className={styles.description}>Conta desativada</span>}
      </td>
      <td>
        {barber.is_active ? (
          <ConfirmButton
            label="Desativar"
            question="Desativar este barbeiro?"
            onConfirm={() => onSetActive(barber, false)}
            busy={busy}
          >
            {others}
          </ConfirmButton>
        ) : (
          <>
            {others}
            <button className={shared.btnIcon} onClick={() => onSetActive(barber, true)} disabled={busy}>
              Reativar
            </button>
          </>
        )}
      </td>
    </tr>
  );
};

export default BarberRow;
