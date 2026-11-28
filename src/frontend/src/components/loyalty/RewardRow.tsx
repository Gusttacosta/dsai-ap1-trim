import CatalogRow from '../CatalogRow';
import type { Reward } from '../../hooks/useLoyaltyAdmin';
import { formatPoints } from '../../utils/loyalty';

// Uma linha da tabela de prêmios do painel (SPEC/2026-11-26-painel-fidelidade.md). "Desativar"
// pede confirmação na própria linha.

export const DEACTIVATE_REWARD_QUESTION =
  'Desativar o prêmio? Ele sai do catálogo, e os resgates feitos continuam no histórico.';

type Props = {
  reward: Reward;
  busy: boolean;
  onEdit: (reward: Reward) => void;
  onDeactivate: (reward: Reward) => void;
};

const RewardRow = ({ reward, busy, onEdit, onDeactivate }: Props) => (
  <CatalogRow
    name={reward.name}
    description={reward.description}
    actionLabel="Desativar"
    question={DEACTIVATE_REWARD_QUESTION}
    busy={busy}
    onEdit={() => onEdit(reward)}
    onConfirm={() => onDeactivate(reward)}
  >
    <td>{formatPoints(reward.points_cost)}</td>
  </CatalogRow>
);

export default RewardRow;
