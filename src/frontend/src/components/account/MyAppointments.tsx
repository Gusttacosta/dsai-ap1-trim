import { useState } from 'react';
import { useMyAppointments, type MyAppointment } from '../../hooks/useMyAppointments';
import { apiErrorMessage } from '../../utils/apiError';
import { splitByStart } from '../../utils/appointmentStatus';
import AccountSection from './AccountSection';
import AppointmentItem from './AppointmentItem';
import styles from './Account.module.css';

// "Meus agendamentos" na conta do cliente (SPEC/2026-11-25-meus-agendamentos.md): próximos e
// anteriores, com o cancelamento pelo PUT /appointments/{id}/cancel.

type GroupProps = {
  title: string;
  empty: string;
  appointments: MyAppointment[];
  barberNames: Record<string, string>;
  busyId: string | null;
  onCancel: (appointment: MyAppointment) => void;
};

const AppointmentGroup = ({ title, empty, appointments, barberNames, busyId, onCancel }: GroupProps) => (
  <div className={styles.group}>
    <h3>{title}</h3>
    {appointments.length === 0 ? (
      <p className={styles.hint}>{empty}</p>
    ) : (
      <ul className={styles.list} aria-label={title}>
        {appointments.map((a) => (
          <AppointmentItem
            key={a.id}
            appointment={a}
            barberName={barberNames[a.barber_id] ?? 'Barbeiro'}
            busy={busyId !== null}
            onCancel={onCancel}
          />
        ))}
      </ul>
    )}
  </div>
);

const MyAppointments = () => {
  const { appointments, barberNames, status, loadError, reload, cancelAppointment } = useMyAppointments();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');

  const cancel = async (appointment: MyAppointment) => {
    setBusyId(appointment.id);
    setActionError('');
    setNotice('');
    try {
      await cancelAppointment(appointment.id);
      setNotice('Agendamento cancelado.');
    } catch (err) {
      setActionError(apiErrorMessage(err, 'Não foi possível cancelar o agendamento.'));
    } finally {
      setBusyId(null);
    }
  };

  const { upcoming, past } = splitByStart(appointments);
  const groupProps = { barberNames, busyId, onCancel: cancel };

  return (
    <AccountSection
      id="agendamentos-titulo"
      title="Meus agendamentos"
      status={status}
      loadError={loadError}
      reload={reload}
      notice={notice}
      actionError={actionError}
    >
      <AppointmentGroup title="Próximos" empty="Nenhum agendamento marcado." appointments={upcoming} {...groupProps} />
      <AppointmentGroup title="Anteriores" empty="Nenhum agendamento anterior." appointments={past} {...groupProps} />
    </AccountSection>
  );
};

export default MyAppointments;
