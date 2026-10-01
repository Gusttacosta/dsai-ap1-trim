import React from 'react';
import { Link } from 'react-router-dom';
import styles from './Landing.module.css';

const Landing = () => {
  return (
    <>
      <section className={styles.hero}>
        <h1 className={styles.title}>
          O Próximo Nível da sua <br />
          <span className={styles.highlight}>Barbearia</span>
        </h1>
        <p className={styles.subtitle}>
          Agendamentos, assinaturas recorrentes, comissionamento automático, fila de espera inteligente e programa de fidelidade. Tudo em uma única plataforma premium.
        </p>
        <div className={styles.actions}>
          <Link to="/agenda" className={styles.btnPrimary}>
            Agendar Horário
          </Link>
          <Link to="/admin" className={styles.btnSecondary}>
            Sou Barbeiro
          </Link>
        </div>
      </section>

      <section className={styles.featuresGrid}>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>📅</div>
          <h3 className={styles.featureTitle}>Agenda Inteligente</h3>
          <p className={styles.featureDesc}>
            Diga adeus ao WhatsApp. Seus clientes marcam sozinhos 24h por dia, com sincronização perfeita e bloqueio de conflitos.
          </p>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>🚶‍♂️</div>
          <h3 className={styles.featureTitle}>Fila de Espera (Walk-in)</h3>
          <p className={styles.featureDesc}>
            Para quem chega sem avisar: uma fila virtual que vira agendamento real assim que o cliente senta na cadeira.
          </p>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>💳</div>
          <h3 className={styles.featureTitle}>Trim Club (Assinaturas)</h3>
          <p className={styles.featureDesc}>
            Receita recorrente garantida. Crie planos mensais para cortes ilimitados e retenha os clientes mais fiéis.
          </p>
        </div>

        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>🏆</div>
          <h3 className={styles.featureTitle}>Fidelidade & Prêmios</h3>
          <p className={styles.featureDesc}>
            Cada corte vale pontos. Cada ponto vira prêmio. Gamifique a experiência e veja os clientes voltarem mais vezes.
          </p>
        </div>
      </section>
    </>
  );
};

export default Landing;

