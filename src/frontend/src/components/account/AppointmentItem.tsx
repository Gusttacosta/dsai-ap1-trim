import type { MyAppointment } from '../../hooks/useMyAppointments';
import { canCancel, STATUS_LABELS } from '../../utils/appointmentStatus';
import { formatPrice } from '../../utils/serviceValidation';
import { formatShopDateTime } from '../../utils/shopDate';
import ConfirmButton from '../ConfirmButton';
import styles from './Account.module.css';

// Um agendamento em "Meus agendamentos" (SPEC/2026-11-25-meus-agendamentos.md): data e hora no
// fuso da barbearia, status, serviços e barbeiro. "Cancelar" só quando a regra do backend deixa.

type Props = {
  appointment: MyAppointment;
  barberName: string;
  /** Um cancelamento está em andamento: os botões ficam desabilitados. */
  busy: boolean;
  onCancel: (appointment: MyAppointment) => void;
};

const AppointmentItem = ({ appointment, barberName, busy, onCancel }: Props) => {
  const when = formatShopDateTime(appointment.start_datetime);
  const services = appointment.items.map((item) => item.service_name).join(' + ');

  return (
    <li className={styles.item} aria-label={`${when}, ${services}`}>
      <div className={styles.itemHeader}>
        <strong>{when}</strong>
        <span className={`${styles.badge} ${styles[`badge_${appointment.status}`] ?? ''}`}>
          {STATUS_LABELS[appointment.status] ?? appointment.status}
        </span>
      </div>
      <p className={styles.itemDetails}>
        {services} · com {barberName} · {formatPrice(appointment.total_price)}
      </p>
      {canCancel(appointment) && (
        <div>
          <ConfirmButton
            label="Cancelar"
            ariaLabel={`Cancelar o agendamento de ${when}`}
            question="Cancelar este agendamento?"
            onConfirm={() => onCancel(appointment)}
            busy={busy}
          />
        </div>
      )}
    </li>
  );
};

export default AppointmentItem;
