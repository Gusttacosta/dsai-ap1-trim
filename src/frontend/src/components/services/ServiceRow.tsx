import shared from '../../pages/AdminShared.module.css';
import { StatusBadge } from '../AdminForm';
import ConfirmButton from '../ConfirmButton';
import type { AdminService } from '../../hooks/useAdminServices';
import { formatPrice } from '../../utils/serviceValidation';
import styles from './Services.module.css';

// Uma linha da tabela de serviços do painel (SPEC/2026-11-23-painel-servicos.md).
// "Desativar" pede confirmação na própria linha (ConfirmButton). "Reativar" não pede.

type Props = {
  service: AdminService;
  /** Uma ação desta linha está em andamento: os botões ficam desabilitados. */
  busy: boolean;
  onEdit: (service: AdminService) => void;
  onDeactivate: (service: AdminService) => void;
  onReactivate: (service: AdminService) => void;
};

const ServiceRow = ({ service, busy, onEdit, onDeactivate, onReactivate }: Props) => {
  const edit = (
    <button className={shared.btnIcon} onClick={() => onEdit(service)} disabled={busy}>
      Editar
    </button>
  );
  const actions = service.is_active ? (
    <ConfirmButton label="Desativar" question="Desativar este serviço?" onConfirm={() => onDeactivate(service)} busy={busy}>
      {edit}
    </ConfirmButton>
  ) : (
    <>
      {edit}
      <button className={shared.btnIcon} onClick={() => onReactivate(service)} disabled={busy}>
        Reativar
      </button>
    </>
  );

  return (
    <tr className={service.is_active ? undefined : styles.inactive} aria-label={service.name}>
      <td style={{ color: '#fff', fontWeight: 500 }}>
        {service.name}
        {service.description && <span className={styles.description}>{service.description}</span>}
      </td>
      <td>{service.duration_minutes} min</td>
      <td>{formatPrice(service.price)}</td>
      <td>
        <StatusBadge active={service.is_active} />
      </td>
      <td>{actions}</td>
    </tr>
  );
};

export default ServiceRow;
