import React, { useState } from 'react';
import styles from './Fidelidade.module.css';

const MOCK_REWARDS = [
  { id: 1, name: 'Sobrancelha na Faixa', desc: 'Faça a sobrancelha totalmente grátis no próximo corte.', cost: 30 },
  { id: 2, name: 'Pomada Modeladora', desc: 'Resgate uma pomada efeito matte.', cost: 80 },
  { id: 3, name: 'Corte Grátis', desc: 'O clássico. Seu próximo corte é por nossa conta!', cost: 150 },
  { id: 4, name: 'Spa Day Completo', desc: 'Corte, barba na toalha quente, sobrancelha e massagem.', cost: 300 },
];

const Fidelidade = () => {
  const [balance, setBalance] = useState(120);

  const handleRedeem = (cost: number, name: string) => {
    if (balance >= cost) {
      setBalance(balance - cost);
      alert(`🎉 Parabéns! Você resgatou: ${name}`);
    }
  };

  return (
    <div className={styles.loyaltyContainer}>
      <div className={styles.walletHeader}>
        <div className={styles.balanceLabel}>Seus Pontos</div>
        <div className={styles.balanceValue}>
          {balance} <span>pts</span>
        </div>
      </div>

      <h2 className={styles.sectionTitle}>🎁 Catálogo de Prêmios</h2>
      
      <div className={styles.rewardsGrid}>
        {MOCK_REWARDS.map(reward => (
          <div key={reward.id} className={styles.rewardCard}>
            <div className={styles.rewardName}>{reward.name}</div>
            <div className={styles.rewardDesc}>{reward.desc}</div>
            <div className={styles.rewardFooter}>
              <span className={styles.rewardCost}>{reward.cost} pts</span>
              <button 
                className={styles.btnRedeem}
                disabled={balance < reward.cost}
                onClick={() => handleRedeem(reward.cost, reward.name)}
              >
                {balance >= reward.cost ? 'Resgatar' : 'Faltam pontos'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Fidelidade;
