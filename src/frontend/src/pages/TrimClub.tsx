import React from 'react';
import styles from './TrimClub.module.css';

const TrimClub = () => {
  return (
    <div className={styles.clubContainer}>
      <div className={styles.header}>
        <h1 className={styles.title}>Trim Club</h1>
        <p className={styles.subtitle}>
          Assine e garanta seu visual impecável o mês inteiro. Escolha o plano que melhor se adapta à sua rotina.
        </p>
      </div>

      <div className={styles.pricingGrid}>
        <div className={styles.planCard}>
          <div className={styles.planName}>Básico</div>
          <div className={styles.planPrice}>
            R$ 80<span>/mês</span>
          </div>
          <ul className={styles.featureList}>
            <li>2 Cortes no mês</li>
            <li>Bebida cortesia</li>
            <li>Cashback de 5%</li>
          </ul>
          <button className={styles.subscribeBtn}>Assinar Básico</button>
        </div>

        <div className={`${styles.planCard} ${styles.popular}`}>
          <div className={styles.popularBadge}>MAIS ASSINADO</div>
          <div className={styles.planName}>Executivo</div>
          <div className={styles.planPrice}>
            R$ 150<span>/mês</span>
          </div>
          <ul className={styles.featureList}>
            <li>Cortes Ilimitados</li>
            <li>Barba a cada 15 dias</li>
            <li>Bebida premium cortesia</li>
            <li>Cashback de 10%</li>
            <li>Prioridade na Fila Walk-in</li>
          </ul>
          <button className={styles.subscribeBtn}>Assinar Executivo</button>
        </div>

        <div className={styles.planCard}>
          <div className={styles.planName}>Barba & Cabelo</div>
          <div className={styles.planPrice}>
            R$ 120<span>/mês</span>
          </div>
          <ul className={styles.featureList}>
            <li>2 Cortes no mês</li>
            <li>2 Barbas no mês</li>
            <li>Bebida cortesia</li>
            <li>Sorteios exclusivos</li>
          </ul>
          <button className={styles.subscribeBtn}>Assinar Barba & Cabelo</button>
        </div>
      </div>
    </div>
  );
};

export default TrimClub;

