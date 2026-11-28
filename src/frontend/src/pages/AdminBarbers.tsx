import { useState } from 'react';
import styles from './AdminShared.module.css';
import LoadState, { ActionFeedback } from '../components/LoadState';
import BarberForm, { type BarberSave } from '../components/barbers/BarberForm';
import BarberRow from '../components/barbers/BarberRow';
import BarberSchedule from '../components/barbers/BarberSchedule';
import UserPicker from '../components/barbers/UserPicker';
import { syncBarberServices, useAdminBarbers, type AdminBarber } from '../hooks/useAdminBarbers';
import type { AdminUser } from '../hooks/useAdminUsers';
import { useRowAction } from '../hooks/useRowAction';

// Barbeiros no painel do admin: lista, novo barbeiro a partir de um usuário, edição do perfil e
// dos serviços, ativar e desativar, e a escala da semana (SPEC/2026-11-26-painel-barbeiros.md).

/** O que está aberto acima da lista. */
type Panel =
  | null
  | { kind: 'pick' }
  | { kind: 'new'; user: AdminUser }
  | { kind: 'edit'; barber: AdminBarber }
  | { kind: 'schedule'; barber: AdminBarber };

const AdminBarbers = () => {
  const { barbers, status, loadError, reload, createBarber, updateBarber, setActive } = useAdminBarbers();
  const [panel, setPanel] = useState<Panel>(null);
  const { busyId, message, actionError, run, clear, setMessage } = useRowAction();

  const open = (next: Panel) => {
    clear();
    setPanel(next);
  };

  const save = async (data: BarberSave) => {
    if (data.kind === 'create') {
      const id = await createBarber(data.input);
      // Daqui em diante o perfil existe: uma falha nos vínculos aparece no topo, e o formulário
      // fecha, para um novo "Salvar" não tentar criar de novo.
      setPanel(null);
      if (data.serviceIds) await run(id, () => syncBarberServices(id, data.serviceIds!), 'Barbeiro criado.');
      else setMessage('Barbeiro criado.');
      return;
    }
    if (panel?.kind !== 'edit') return;
    const { id } = panel.barber;
    if (Object.keys(data.changes).length > 0) await updateBarber(id, data.changes);
    if (data.serviceIds) await syncBarberServices(id, data.serviceIds);
    setPanel(null);
    setMessage('Barbeiro atualizado.');
  };

  const onSetActive = (barber: AdminBarber, isActive: boolean) =>
    run(barber.id, () => setActive(barber.id, isActive), isActive ? 'Barbeiro reativado.' : 'Barbeiro desativado.');

  let form = null;
  if (panel?.kind === 'pick') {
    form = (
      <UserPicker
        barberUserIds={new Set(barbers.map((b) => b.user_id))}
        onPick={(user) => setPanel({ kind: 'new', user })}
        onCancel={() => setPanel(null)}
      />
    );
  } else if (panel?.kind === 'new' || panel?.kind === 'edit') {
    form = (
      <BarberForm
        // Trocar de barbeiro ou de usuário recria o formulário com os dados do novo.
        key={panel.kind === 'new' ? `new-${panel.user.id}` : panel.barber.id}
        barber={panel.kind === 'edit' ? panel.barber : undefined}
        user={panel.kind === 'new' ? panel.user : undefined}
        onChangeUser={panel.kind === 'new' ? () => setPanel({ kind: 'pick' }) : undefined}
        onSave={save}
        onCancel={() => setPanel(null)}
      />
    );
  } else if (panel?.kind === 'schedule') {
    form = (
      <BarberSchedule
        key={panel.barber.id}
        barberId={panel.barber.id}
        barberName={panel.barber.full_name}
        onSaved={() => {
          setPanel(null);
          setMessage('Escala salva.');
        }}
        onCancel={() => setPanel(null)}
      />
    );
  }

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>💈 Barbeiros</h2>
        <button className={styles.btnAction} onClick={() => open({ kind: 'pick' })} disabled={status !== 'ready'}>
          + Novo Barbeiro
        </button>
      </div>

      {form}

      <ActionFeedback message={message} error={actionError} />

      <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando barbeiros...">
        {barbers.length === 0 ? (
          <p>Nenhum barbeiro cadastrado.</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Barbeiro</th>
                <th>Comissão</th>
                <th>Situação</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {barbers.map((barber) => (
                <BarberRow
                  key={barber.id}
                  barber={barber}
                  busy={busyId === barber.id}
                  onEdit={(b) => open({ kind: 'edit', barber: b })}
                  onSchedule={(b) => open({ kind: 'schedule', barber: b })}
                  onSetActive={onSetActive}
                />
              ))}
            </tbody>
          </table>
        )}
      </LoadState>
    </div>
  );
};

export default AdminBarbers;
