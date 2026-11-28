import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import styles from './TrimClub.module.css';
import { planBenefits } from '../utils/trimClub';

// Campos de GET /subscriptions/plans. A tela lia `price` e `billing_cycle`, que a API não tem, e
// mostrava "R$ NaN/ano" (SPEC/2026-11-25-alembic-migracoes.md).
export interface Plan {
  id: string;
  name: string;
  description: string | null;
  monthly_price: string | number;
  /** null = ilimitado (#16) */
  included_cuts: number | null;
  included_shaves: number | null;
}

const TrimClub = () => {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        const response = await api.get('/subscriptions/plans');
        setPlans(response.data);
      } catch (error) {
        console.error('Erro ao buscar planos', error);
      } finally {
        setLoading(false);
      }
    };
    fetchPlans();
  }, []);

  const handleSubscribe = async (planId: string) => {
    try {
      await api.post(`/subscriptions/me/subscribe/${planId}`);
      alert('Assinatura realizada com sucesso! Bem-vindo ao Trim Club!');
      navigate('/');
    } catch (err: any) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        alert('Você precisa estar logado como Cliente para assinar.');
        navigate('/login');
      } else {
        alert(err.response?.data?.detail || 'Erro ao realizar assinatura.');
      }
    }
  };

  if (loading) {
    return <div style={{ color: '#fff', textAlign: 'center', marginTop: '4rem' }}>Carregando planos...</div>;
  }

  return (
    <div className={styles.clubContainer}>
      <div className={styles.header}>
        <h1 className={styles.title}>Trim Club</h1>
        <p className={styles.subtitle}>
          Assine e garanta seu visual impecável o mês inteiro. Escolha o plano que melhor se adapta à sua rotina.
        </p>
      </div>

      <div className={styles.pricingGrid}>
        {plans.map((plan, index) => (
          <div key={plan.id} className={`${styles.planCard} ${index === 1 ? styles.popular : ''}`}>
            {index === 1 && <div className={styles.popularBadge}>MAIS ASSINADO</div>}
            <div className={styles.planName}>{plan.name}</div>
            <div className={styles.planPrice}>
              R$ {Number(plan.monthly_price).toFixed(2).replace('.', ',')}<span>/mês</span>
            </div>
            <ul className={styles.featureList}>
              {planBenefits(plan).map((benefit) => (
                <li key={benefit}>{benefit}</li>
              ))}
              {(plan.description ?? '')
                .split(',')
                .map((feature) => feature.trim())
                .filter(Boolean)
                .map((feature, i) => (
                  <li key={i}>{feature}</li>
                ))}
            </ul>
            <button className={styles.subscribeBtn} onClick={() => handleSubscribe(plan.id)}>
              Assinar {plan.name}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TrimClub;

