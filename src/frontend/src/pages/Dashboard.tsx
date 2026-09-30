import React, { useState } from 'react';
import { useNavigate, Routes, Route, Link, useLocation } from 'react-router-dom';
import styles from './Dashboard.module.css';

import AdminStore from './AdminStore';
import AdminServices from './AdminServices';
import AdminFinance from './AdminFinance';
import AdminNotifications from './AdminNotifications';

const MOCK_QUEUE = [
  { id: 1, name: 'Marcos Almeida', service: 'Corte + Barba', waitTime: '15 min' },
  { id: 2, name: 'Pedro H.', service: 'Degradê', waitTime: '5 min' },
];

const Overview = () => {
  const [queue, setQueue] = useState(MOCK_QUEUE);
  return (
    <>
      <div className={styles.header}>
        <h2 className={styles.title}>Visão Geral de Hoje</h2>
      </div>
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statTitle}>Faturamento (Hoje)</div>
          <div className={`${styles.statValue} ${styles.statHighlight}`}>R$ 840,00</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statTitle}>Cortes Finalizados</div>
          <div className={styles.statValue}>12</div>
        </div>
      </div>
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
                <button className={styles.queueAction} onClick={() => setQueue(queue.filter(q => q.id !== item.id))}>
                  Atender Agora
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

const Dashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const getNavClass = (path: string) => {
    return `${styles.navItem} ${location.pathname === path ? styles.active : ''}`;
  };

  return (
    <div className={styles.dashboardContainer}>
      {/* Sidebar */}
      <div className={styles.sidebar}>
        <div className={styles.logo} onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          Trim Admin
        </div>
        <Link to="/admin" className={getNavClass('/admin')}>Painel Principal</Link>
        <Link to="/admin/loja" className={getNavClass('/admin/loja')}>Loja & Estoque</Link>
        <Link to="/admin/servicos" className={getNavClass('/admin/servicos')}>Serviços</Link>
        <Link to="/admin/financeiro" className={getNavClass('/admin/financeiro')}>Financeiro</Link>
        <Link to="/admin/notificacoes" className={getNavClass('/admin/notificacoes')}>Notificações</Link>
      </div>

      {/* Main Content */}
      <div className={styles.mainArea}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/loja" element={<AdminStore />} />
          <Route path="/servicos" element={<AdminServices />} />
          <Route path="/financeiro" element={<AdminFinance />} />
          <Route path="/notificacoes" element={<AdminNotifications />} />
        </Routes>
      </div>
    </div>
  );
};

export default Dashboard;
