import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './Dashboard.module.css';

const MOCK_QUEUE = [
  { id: 1, name: 'Marcos Almeida', service: 'Corte + Barba', waitTime: '15 min' },
  { id: 2, name: 'Pedro H.', service: 'Degradê', waitTime: '5 min' },
];

const Dashboard = () => {
  const navigate = useNavigate();
  const [queue, setQueue] = useState(MOCK_QUEUE);

  const handleAttend = (id: number) => {
    setQueue(queue.filter((q) => q.id !== id));
    alert('Cliente encaminhado para a cadeira! (Appointment IN_PROGRESS criado)');
  };

  return (
    <div className={styles.dashboardContainer}>
      {/* Sidebar */}
      <div className={styles.sidebar}>
        <div className={styles.logo} onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          Trim Admin
        </div>
        <div className={`${styles.navItem} ${styles.active}`}>Painel Principal</div>
        <div className={styles.navItem}>Fila Walk-in</div>
        <div className={styles.navItem}>Agenda do Dia</div>
        <div className={styles.navItem}>Caixa & Comissões</div>
        <div className={styles.navItem}>Galeria (Aprovações)</div>
      </div>

      {/* Main Content */}
      <div className={styles.mainArea}>
        <div className={styles.header}>
          <h2 className={styles.title}>Visão Geral de Hoje</h2>
          <div>
            <span style={{ color: 'var(--color-text-secondary)', marginRight: '1rem' }}>
              Barbeiro: <strong>João Silva</strong>
            </span>
          </div>
        </div>

        {/* Stats */}
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statTitle}>Faturamento (Hoje)</div>
            <div className={`${styles.statValue} ${styles.statHighlight}`}>R$ 840,00</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statTitle}>Cortes Finalizados</div>
            <div className={styles.statValue}>12</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statTitle}>Na Fila de Espera</div>
            <div className={styles.statValue}>{queue.length}</div>
          </div>
        </div>

        {/* Queue Management */}
        <div className={styles.queueSection}>
          <h3 className={styles.queueTitle}>Fila de Espera (Ao Vivo)</h3>
          {queue.length === 0 ? (
            <p style={{ color: 'var(--color-text-secondary)' }}>Nenhum cliente na fila.</p>
          ) : (
            <div className={styles.queueList}>
              {queue.map((item) => (
                <div key={item.id} className={styles.queueItem}>
                  <div className={styles.queueInfo}>
                    <h4>{item.name}</h4>
                    <p>{item.service} • Esperando há {item.waitTime}</p>
                  </div>
                  <button className={styles.queueAction} onClick={() => handleAttend(item.id)}>
                    Atender Agora
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
