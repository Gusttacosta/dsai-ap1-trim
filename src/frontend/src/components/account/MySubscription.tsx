import { Link } from 'react-router-dom';
import { useRowAction } from '../../hooks/useRowAction';
import { useMySubscription, type Subscription } from '../../hooks/useTrimClub';
import { formatPrice } from '../../utils/serviceValidation';
import { formatIsoDate } from '../../utils/shopDate';
import { planBenefitsWithDiscount, SUBSCRIPTION_STATUS_LABELS } from '../../utils/trimClub';
import { StatusBadge } from '../AdminForm';
import ConfirmButton from '../ConfirmButton';
import AccountSection from './AccountSection';
import styles from './Account.module.css';

// "Trim Club" na conta do cliente (SPEC/2026-11-26-painel-trim-club.md): a assinatura, a validade
// e o cancelamento pelo PUT /subscriptions/me/cancel, com confirmação. Sem assinatura, o convite
// para a vitrine.

export const CANCELED_NOTICE = 'Assinatura cancelada.';

/** A validade, conforme a situação. */
function validity({ status, end_date }: Subscription): string {
  const end = formatIsoDate(end_date);
  if (status === 'canceled') return `Cancelada. Seus benefícios valem até ${end}.`;
  if (status === 'past_due') return `Venceu em ${end}.`;
  return `Renova em ${end}.`;
}

const SubscriptionDetails = ({ subscription, busy, onCancel }: {
  subscription: Subscription;
  busy: boolean;
  onCancel: () => void;
}) => {
  const { plan, status } = subscription;
  return (
    <div className={styles.item} aria-label={`Assinatura ${plan.name}`}>
      <div className={styles.itemHeader}>
        <strong>
          {plan.name} · {formatPrice(plan.monthly_price)}/mês
        </strong>
        <StatusBadge active={status === 'active'} label={SUBSCRIPTION_STATUS_LABELS[status]} />
      </div>
      {planBenefitsWithDiscount(plan).map((benefit) => (
        <p key={benefit} className={styles.itemDetails}>
          {benefit}
        </p>
      ))}
      <p className={styles.itemDetails}>{validity(subscription)}</p>
      {status === 'active' && (
        <div>
          <ConfirmButton
            label="Cancelar assinatura"
            question={`Cancelar a assinatura? Os benefícios valem até ${formatIsoDate(subscription.end_date)}.`}
            onConfirm={onCancel}
            busy={busy}
          />
        </div>
      )}
      {status === 'past_due' && <Link to="/club">Assinar de novo</Link>}
    </div>
  );
};

const MySubscription = () => {
  const { subscription, status, loadError, reload, cancel } = useMySubscription();
  const { busyId, message, actionError, run } = useRowAction();

  return (
    <AccountSection
      id="trim-club-titulo"
      title="Trim Club"
      status={status}
      loadError={loadError}
      reload={reload}
      notice={message}
      actionError={actionError}
    >
      {subscription ? (
        <SubscriptionDetails
          subscription={subscription}
          busy={busyId !== null}
          onCancel={() => run(subscription.id, cancel, CANCELED_NOTICE)}
        />
      ) : (
        <p className={styles.hint}>
          Você ainda não é sócio do Trim Club. <Link to="/club">Conhecer os planos</Link>
        </p>
      )}
    </AccountSection>
  );
};

export default MySubscription;
