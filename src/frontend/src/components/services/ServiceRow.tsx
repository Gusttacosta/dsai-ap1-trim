import { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import type { AdminService } from '../../hooks/useAdminServices';
import { formatPrice } from '../../utils/serviceValidation';
import styles from './Services.module.css';

// Uma linha da tabela de serviços do painel (SPEC/2026-11-23-painel-servicos.md).
// "Desativar" pede confirmação na própria linha. "Reativar" não pede.

type Props = {
  service: AdminService;
  /** Uma ação desta linha está em andamento: os botões ficam desabilitados. */
  busy: boolean;
  onEdit: (service: AdminService) => void;
  onDeactivate: (service: AdminService) => void;
  onReactivate: (service: AdminService) => void;
};

const ServiceRow = ({ service, busy, onEdit, onDeactivate, onReactivate }: Props) => {
  const [confirming, setConfirming] = useState(false);

  const confirmDeactivation = () => {
    setConfirming(false);
    onDeactivate(service);
  };

  let actions;
  if (confirming) {
    actions = (
      <>
        <span className={styles.confirm}>Desativar este serviço?</span>
        <button className={`${shared.btnIcon} ${shared.btnDanger}`} onClick={confirmDeactivation} disabled={busy}>
          Confirmar
        </button>
        <button className={shared.btnIcon} onClick={() => setConfirming(false)} disabled={busy}>
          Voltar
        </button>
      </>
    );
  } else {
    actions = (
      <>
        <button className={shared.btnIcon} onClick={() => onEdit(service)} disabled={busy}>
          Editar
        </button>
        {service.is_active ? (
          <button className={`${shared.btnIcon} ${shared.btnDanger}`} onClick={() => setConfirming(true)} disabled={busy}>
            Desativar
          </button>
        ) : (
          <button className={shared.btnIcon} onClick={() => onReactivate(service)} disabled={busy}>
            Reativar
          </button>
        )}
      </>
    );
  }

  return (
    <tr className={service.is_active ? undefined : styles.inactive} aria-label={service.name}>
      <td style={{ color: '#fff', fontWeight: 500 }}>
        {service.name}
        {service.description && <span className={styles.description}>{service.description}</span>}
      </td>
      <td>{service.duration_minutes} min</td>
      <td>{formatPrice(service.price)}</td>
      <td>
        <span className={`${styles.badge} ${service.is_active ? styles.badgeActive : styles.badgeInactive}`}>
          {service.is_active ? 'Ativo' : 'Desativado'}
        </span>
      </td>
      <td>{actions}</td>
    </tr>
  );
};

export default ServiceRow;
