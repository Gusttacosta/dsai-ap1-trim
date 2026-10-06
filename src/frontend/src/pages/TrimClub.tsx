import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import styles from './TrimClub.module.css';

interface Plan {
  id: string;
  name: string;
  description: string;
  price: number;
  billing_cycle: string;
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
              R$ {Number(plan.price).toFixed(2)}<span>/{plan.billing_cycle === 'MONTHLY' ? 'mês' : 'ano'}</span>
            </div>
            <ul className={styles.featureList}>
              {plan.description.split(',').map((feature, i) => (
                <li key={i}>{feature.trim()}</li>
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

