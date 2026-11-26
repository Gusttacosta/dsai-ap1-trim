import { useState } from 'react';
import styles from './AdminShared.module.css';
import LoadState, { ActionFeedback } from '../components/LoadState';
import AdjustPointsForm from '../components/loyalty/AdjustPointsForm';
import RedemptionTable from '../components/loyalty/RedemptionTable';
import RewardForm from '../components/loyalty/RewardForm';
import RewardRow from '../components/loyalty/RewardRow';
import WalletTable from '../components/loyalty/WalletTable';
import { useRowAction } from '../hooks/useRowAction';
import {
  useAdminRewards,
  useRedemptions,
  useWallets,
  type AdjustAction,
  type Reward,
  type RewardChanges,
  type RewardInput,
  type Wallet,
} from '../hooks/useLoyaltyAdmin';

// Aba "Fidelidade" do painel, só do admin (SPEC/2026-11-26-painel-fidelidade.md): os prêmios, com
// criação, edição e desativação confirmada, as carteiras com o ajuste manual de pontos (motivo
// obrigatório e confirmação) e o histórico de resgates.

/** Formulário de prêmio aberto: nenhum, o de criação ou o de edição de um prêmio. */
type Editing = null | 'new' | Reward;

const AdminLoyalty = () => {
  const { rewards, status, loadError, reload, createReward, updateReward, deactivateReward } = useAdminRewards();
  const wallets = useWallets();
  const redemptions = useRedemptions();
  const [editing, setEditing] = useState<Editing>(null);
  const [adjusting, setAdjusting] = useState<Wallet | null>(null);
  const { busyId, message, actionError, run, clear, setMessage } = useRowAction();

  const open = (target: Editing) => {
    clear();
    setAdjusting(null);
    setEditing(target);
  };

  const openAdjust = (wallet: Wallet) => {
    clear();
    setEditing(null);
    setAdjusting(wallet);
  };

  const save = async (data: RewardInput | RewardChanges) => {
    if (editing === 'new') {
      await createReward(data as RewardInput);
      setMessage('Prêmio criado.');
    } else if (editing) {
      await updateReward(editing.id, data);
      setMessage('Prêmio atualizado.');
    }
    setEditing(null);
  };

  const deactivate = (reward: Reward) => {
    if (editing !== 'new' && editing?.id === reward.id) setEditing(null);
    run(reward.id, () => deactivateReward(reward.id), 'Prêmio desativado. Ele saiu do catálogo.');
  };

  const adjust = async (action: AdjustAction, points: number, reason: string) => {
    if (!adjusting) return;
    await wallets.adjust(adjusting, action, points, reason);
    setMessage(action === 'add' ? 'Pontos adicionados.' : 'Pontos retirados.');
    setAdjusting(null);
  };

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>🎁 Fidelidade</h2>
        <button className={styles.btnAction} onClick={() => open('new')} disabled={status !== 'ready'}>
          + Novo prêmio
        </button>
      </div>

      {editing && (
        <RewardForm
          // Trocar de prêmio recria o formulário com os dados do novo.
          key={editing === 'new' ? 'new' : editing.id}
          reward={editing === 'new' ? undefined : editing}
          onSave={save}
          onCancel={() => setEditing(null)}
        />
      )}

      {adjusting && <AdjustPointsForm wallet={adjusting} onSave={adjust} onCancel={() => setAdjusting(null)} />}

      <ActionFeedback message={message} error={actionError} />

      <h3 className={styles.title}>Prêmios</h3>
      <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando prêmios...">
        {rewards.length === 0 ? (
          <p>Nenhum prêmio cadastrado.</p>
        ) : (
          <table className={styles.table} aria-label="Prêmios">
            <thead>
              <tr>
                <th>Prêmio</th>
                <th>Custo</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {rewards.map((reward) => (
                <RewardRow
                  key={reward.id}
                  reward={reward}
                  busy={busyId === reward.id}
                  onEdit={open}
                  onDeactivate={deactivate}
                />
              ))}
            </tbody>
          </table>
        )}
      </LoadState>

      <h3 className={styles.title} style={{ marginTop: '2.5rem' }}>Carteiras</h3>
      <LoadState status={wallets.status} loadError={wallets.loadError} reload={wallets.reload} loadingText="Carregando carteiras...">
        <WalletTable wallets={wallets.wallets} busy={adjusting !== null} onAdjust={openAdjust} />
      </LoadState>

      <h3 className={styles.title} style={{ marginTop: '2.5rem' }}>Resgates</h3>
      <LoadState
        status={redemptions.status}
        loadError={redemptions.loadError}
        reload={redemptions.reload}
        loadingText="Carregando resgates..."
      >
        <RedemptionTable redemptions={redemptions.redemptions} wallets={wallets.wallets} />
      </LoadState>
    </div>
  );
};

export default AdminLoyalty;
