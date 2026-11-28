import shared from '../../pages/AdminShared.module.css';
import type { Subscriber, Subscription } from '../../hooks/useTrimClub';
import { formatIsoDate } from '../../utils/shopDate';
import { SUBSCRIPTION_STATUS_LABELS } from '../../utils/trimClub';
import { StatusBadge } from '../AdminForm';
import styles from '../services/Services.module.css';

// Assinantes do Trim Club no painel, só de leitura (SPEC/2026-11-26-painel-trim-club.md): o
// cliente, o plano, as datas e a situação, na ordem do backend (a mais nova primeiro).

type Props = {
  subscriptions: Subscription[];
  subscribers: Record<string, Subscriber>;
};

const SubscriptionTable = ({ subscriptions, subscribers }: Props) => {
  if (subscriptions.length === 0) return <p>Nenhum assinante ainda.</p>;
  return (
    <table className={shared.table} aria-label="Assinantes">
      <thead>
        <tr>
          <th>Cliente</th>
          <th>Plano</th>
          <th>Início</th>
          <th>Fim</th>
          <th>Situação</th>
        </tr>
      </thead>
      <tbody>
        {subscriptions.map((sub) => {
          const person = subscribers[sub.user_id];
          const name = person?.full_name ?? 'Cliente não encontrado';
          return (
            <tr key={sub.id} aria-label={name}>
              <td style={{ color: '#fff', fontWeight: 500 }}>
                {name}
                {person && <span className={styles.description}>{person.email}</span>}
              </td>
              <td>{sub.plan.name}</td>
              <td>{formatIsoDate(sub.start_date)}</td>
              <td>{formatIsoDate(sub.end_date)}</td>
              <td>
                <StatusBadge active={sub.status === 'active'} label={SUBSCRIPTION_STATUS_LABELS[sub.status]} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
};

export default SubscriptionTable;
