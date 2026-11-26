import { useState } from 'react';
import styles from './AdminShared.module.css';
import LoadState, { ActionFeedback } from '../components/LoadState';
import PlanForm from '../components/trimClub/PlanForm';
import PlanRow from '../components/trimClub/PlanRow';
import SubscriptionTable from '../components/trimClub/SubscriptionTable';
import { useRowAction } from '../hooks/useRowAction';
import {
  useAdminPlans,
  useSubscriptions,
  type PlanChanges,
  type PlanInput,
  type SubscriptionPlan,
} from '../hooks/useTrimClub';

// Aba "Trim Club" do painel, só do admin (SPEC/2026-11-26-painel-trim-club.md): os planos, com
// criação, edição e exclusão confirmada, e a lista de assinantes.

/** Formulário aberto: nenhum, o de criação ou o de edição de um plano. */
type Editing = null | 'new' | SubscriptionPlan;

const AdminTrimClub = () => {
  const { plans, status, loadError, reload, createPlan, updatePlan, removePlan } = useAdminPlans();
  const subscriptions = useSubscriptions();
  const [editing, setEditing] = useState<Editing>(null);
  const { busyId, message, actionError, run, clear, setMessage } = useRowAction();

  const open = (target: Editing) => {
    clear();
    setEditing(target);
  };

  const save = async (data: PlanInput | PlanChanges) => {
    if (editing === 'new') {
      await createPlan(data as PlanInput);
      setMessage('Plano criado.');
    } else if (editing) {
      await updatePlan(editing.id, data);
      setMessage('Plano atualizado.');
    }
    setEditing(null);
  };

  const remove = (plan: SubscriptionPlan) => {
    if (editing !== 'new' && editing?.id === plan.id) setEditing(null);
    run(plan.id, () => removePlan(plan.id), 'Plano excluído. Ele saiu da vitrine.');
  };

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>👑 Trim Club</h2>
        <button className={styles.btnAction} onClick={() => open('new')} disabled={status !== 'ready'}>
          + Novo plano
        </button>
      </div>

      {editing && (
        <PlanForm
          // Trocar de plano recria o formulário com os dados do novo.
          key={editing === 'new' ? 'new' : editing.id}
          plan={editing === 'new' ? undefined : editing}
          onSave={save}
          onCancel={() => setEditing(null)}
        />
      )}

      <ActionFeedback message={message} error={actionError} />

      <h3 className={styles.title}>Planos</h3>
      <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando planos...">
        {plans.length === 0 ? (
          <p>Nenhum plano cadastrado.</p>
        ) : (
          <table className={styles.table} aria-label="Planos">
            <thead>
              <tr>
                <th>Plano</th>
                <th>Preço</th>
                <th>Benefícios</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((plan) => (
                <PlanRow key={plan.id} plan={plan} busy={busyId === plan.id} onEdit={open} onDelete={remove} />
              ))}
            </tbody>
          </table>
        )}
      </LoadState>

      <h3 className={styles.title} style={{ marginTop: '2.5rem' }}>Assinantes</h3>
      <LoadState
        status={subscriptions.status}
        loadError={subscriptions.loadError}
        reload={subscriptions.reload}
        loadingText="Carregando assinantes..."
      >
        <SubscriptionTable subscriptions={subscriptions.subscriptions} subscribers={subscriptions.subscribers} />
      </LoadState>
    </div>
  );
};

export default AdminTrimClub;
