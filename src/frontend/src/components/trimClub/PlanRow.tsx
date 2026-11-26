import CatalogRow from '../CatalogRow';
import type { SubscriptionPlan } from '../../hooks/useTrimClub';
import { formatPrice } from '../../utils/serviceValidation';
import { planBenefitsWithDiscount } from '../../utils/trimClub';

// Uma linha da tabela de planos do painel (SPEC/2026-11-26-painel-trim-club.md). "Excluir" pede
// confirmação na própria linha; o backend só desativa o plano.

export const DELETE_PLAN_QUESTION = 'Excluir o plano? Ele sai da vitrine, e quem já assina continua com ele.';

type Props = {
  plan: SubscriptionPlan;
  /** Uma ação desta linha está em andamento: os botões ficam desabilitados. */
  busy: boolean;
  onEdit: (plan: SubscriptionPlan) => void;
  onDelete: (plan: SubscriptionPlan) => void;
};

const PlanRow = ({ plan, busy, onEdit, onDelete }: Props) => {
  const benefits = planBenefitsWithDiscount(plan);
  return (
    <CatalogRow
      name={plan.name}
      description={plan.description}
      actionLabel="Excluir"
      question={DELETE_PLAN_QUESTION}
      busy={busy}
      onEdit={() => onEdit(plan)}
      onConfirm={() => onDelete(plan)}
    >
      <td>{formatPrice(plan.monthly_price)}/mês</td>
      <td>{benefits.length ? benefits.join(' · ') : 'Sem benefícios inclusos'}</td>
    </CatalogRow>
  );
};

export default PlanRow;
