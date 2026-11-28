import { isAxiosError } from 'axios';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { apiErrorMessage } from '../utils/apiError';
import styles from './Fidelidade.module.css';

// Programa de fidelidade ligado à API (SPEC/2026-11-25-fidelidade-pontos.md, #13). Antes, os
// prêmios eram fixos no código, o saldo começava sempre em 120 e o resgate não chegava ao servidor.

type Reward = { id: string; name: string; description: string | null; points_cost: number };
type Wallet = { balance: number; lifetime_points: number };

const Fidelidade = () => {
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loggedOut, setLoggedOut] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [redeeming, setRedeeming] = useState<string | null>(null);

  const loadWallet = useCallback(async () => {
    try {
      const response = await api.get<Wallet>('/loyalty/me');
      setWallet(response.data);
      setLoggedOut(false);
    } catch (err) {
      const status = isAxiosError(err) ? err.response?.status : undefined;
      if (status === 401 || status === 403) setLoggedOut(true);
      else setError(apiErrorMessage(err, 'Não foi possível carregar o seu saldo.'));
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const response = await api.get<Reward[]>('/loyalty/rewards');
        if (active) setRewards(Array.isArray(response.data) ? response.data : []);
      } catch (err) {
        if (active) setError(apiErrorMessage(err, 'Não foi possível carregar os prêmios.'));
      }
      await loadWallet();
      if (active) setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [loadWallet]);

  const handleRedeem = async (reward: Reward) => {
    setError('');
    setSuccess('');
    setRedeeming(reward.id);
    try {
      await api.post(`/loyalty/redeem/${reward.id}`);
      setSuccess(`🎉 Você resgatou: ${reward.name}. Mostre esta tela na barbearia.`);
      await loadWallet();
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível resgatar o prêmio.'));
    } finally {
      setRedeeming(null);
    }
  };

  const balance = wallet?.balance ?? 0;

  return (
    <div className={styles.loyaltyContainer}>
      <div className={styles.walletHeader}>
        <div className={styles.balanceLabel}>Seus Pontos</div>
        {loggedOut ? (
          <p>
            <Link to="/login">Entre na sua conta</Link> para ver o saldo e resgatar prêmios. Cada real gasto
            em atendimentos e na loja vale 1 ponto.
          </p>
        ) : (
          <div className={styles.balanceValue} data-testid="saldo">
            {loading ? '...' : balance} <span>pts</span>
          </div>
        )}
      </div>

      {error && <p role="alert">{error}</p>}
      {success && <p role="status">{success}</p>}

      <h2 className={styles.sectionTitle}>🎁 Catálogo de Prêmios</h2>

      {!loading && rewards.length === 0 && <p>Nenhum prêmio disponível no momento.</p>}

      <div className={styles.rewardsGrid}>
        {rewards.map((reward) => {
          const enough = !loggedOut && balance >= reward.points_cost;
          return (
            <div key={reward.id} className={styles.rewardCard}>
              <div className={styles.rewardName}>{reward.name}</div>
              {reward.description && <div className={styles.rewardDesc}>{reward.description}</div>}
              <div className={styles.rewardFooter}>
                <span className={styles.rewardCost}>{reward.points_cost} pts</span>
                <button
                  className={styles.btnRedeem}
                  disabled={!enough || redeeming !== null}
                  onClick={() => handleRedeem(reward)}
                  aria-label={`Resgatar ${reward.name}`}
                >
                  {loggedOut ? 'Entre para resgatar' : enough ? 'Resgatar' : 'Faltam pontos'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Fidelidade;
