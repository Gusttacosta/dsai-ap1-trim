import { useState, useEffect } from 'react';
import { useNavigate, Routes, Route, Link, useLocation } from 'react-router-dom';
import styles from './Dashboard.module.css';
import api, { logout } from '../api';
import { canFinish } from '../utils/appointmentStatus';
import { CHANGE_PASSWORD_PATH } from '../utils/afterLogin';

import AdminStore from './AdminStore';
import AdminServices from './AdminServices';
import AdminFinance from './AdminFinance';
import AdminExpenses from './AdminExpenses';
import AdminNotifications from './AdminNotifications';
import AdminUsers from './AdminUsers';
import AdminBarbers from './AdminBarbers';
import Account from './Account';

const Overview = ({ user }: { user: any }) => {
  const [queue, setQueue] = useState<any[]>([]);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({ total_revenue: 0, completed_appointments: 0 });

  useEffect(() => {
    if (!user) return;
    
    if (user.role === 'admin') {
      // Busca dados do dashboard
      api.get('/reports/daily-overview').then(res => {
        setStats(res.data);
      }).catch(console.error);

      // Busca fila
      api.get('/queue/live').then(res => {
        setQueue(res.data);
      }).catch(console.error);
    } else if (user.role === 'barber') {
      api.get('/reports/me').then(res => {
        setStats({ 
          total_revenue: res.data.total_revenue_generated, 
          completed_appointments: res.data.total_appointments 
        });
      }).catch(console.error);

      api.get('/appointments/barber/me').then(res => {
        setAppointments(res.data);
      }).catch(console.error);
    }
  }, [user]);

  return (
    <>
      <div className={styles.header}>
        <h2 className={styles.title}>Bem-vindo(a), {user?.full_name || 'Admin'}!</h2>
      </div>
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statTitle}>Faturamento (Hoje)</div>
          <div className={`${styles.statValue} ${styles.statHighlight}`}>R$ {Number(stats.total_revenue).toFixed(2)}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statTitle}>Cortes Finalizados</div>
          <div className={styles.statValue}>{stats.completed_appointments}</div>
        </div>
      </div>
      
      {user.role === 'admin' && (
        <div className={styles.queueSection}>
          <h3 className={styles.queueTitle}>Fila de Espera (Ao Vivo)</h3>
          {queue.length === 0 ? (
            <p style={{ color: 'var(--color-text-secondary)' }}>Nenhum cliente na fila.</p>
          ) : (
            <div className={styles.queueList}>
              {queue.map((item: any, idx: number) => (
                <div key={idx} className={styles.queueItem}>
                  <div className={styles.queueInfo}>
                    <h4>{item.customer_name_masked}</h4>
                    <p>Posição {item.position} • Entrou às {new Date(item.joined_at).toLocaleTimeString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {user.role === 'barber' && (
        <div className={styles.queueSection}>
          <h3 className={styles.queueTitle}>Meus Agendamentos (Hoje)</h3>
          {appointments.length === 0 ? (
            <p style={{ color: 'var(--color-text-secondary)' }}>Nenhum agendamento para hoje.</p>
          ) : (
            <div className={styles.queueList}>
              {appointments.filter((a: any) => new Date(a.start_datetime).toDateString() === new Date().toDateString()).map((item: any) => (
                <div key={item.id} className={styles.queueItem} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className={styles.queueInfo}>
                    <h4>{item.notes ? item.notes : 'Cliente'}</h4>
                    <p>{item.start_datetime.substring(11, 16)} • {item.status}</p>
                  </div>
                  {canFinish(item) && (
                    <button 
                      onClick={() => {
                        api.put(`/appointments/${item.id}/status`, { status: "completed" })
                          .then(() => {
                            setAppointments(prev => prev.map(a => a.id === item.id ? { ...a, status: 'completed' } : a));
                            setStats((s: any) => ({ ...s, completed_appointments: s.completed_appointments + 1, total_revenue: s.total_revenue + Number(item.total_price) }));
                          })
                          .catch((err: any) => {
                            alert(`Não foi possível finalizar: ${err.response?.data?.detail || 'erro desconhecido.'}`);
                          });
                      }}
                      style={{ padding: '0.5rem 1rem', background: 'var(--color-primary)', color: '#000', borderRadius: '8px', fontWeight: 'bold', border: 'none', cursor: 'pointer' }}
                    >
                      Finalizar
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}

const Dashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await api.get('/auth/me');
        // Senha temporária pendente: o resto da API responde 403 até a troca (#99).
        if (response.data.must_change_password) {
          navigate(CHANGE_PASSWORD_PATH, { replace: true });
          return;
        }
        setUser(response.data);
      } catch (err) {
        localStorage.removeItem('token');
        navigate('/admin/login');
      }
    };
    fetchUser();
  }, [navigate]);

  const getNavClass = (path: string) => {
    return `${styles.navItem} ${location.pathname === path ? styles.active : ''}`;
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!user) return <div style={{ padding: '2rem' }}>Carregando...</div>;

  return (
    <div className={styles.dashboardContainer}>
      {/* Sidebar */}
      <div className={styles.sidebar}>
        <div className={styles.logo} onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          Trim Admin
        </div>
        <Link to="/admin" className={getNavClass('/admin')}>Painel Principal</Link>
        {user.role === 'admin' && (
          <>
            <Link to="/admin/loja" className={getNavClass('/admin/loja')}>Loja & Estoque</Link>
            <Link to="/admin/servicos" className={getNavClass('/admin/servicos')}>Serviços</Link>
            <Link to="/admin/barbeiros" className={getNavClass('/admin/barbeiros')}>Barbeiros</Link>
            <Link to="/admin/financeiro" className={getNavClass('/admin/financeiro')}>Financeiro</Link>
            <Link to="/admin/despesas" className={getNavClass('/admin/despesas')}>Despesas</Link>
            <Link to="/admin/notificacoes" className={getNavClass('/admin/notificacoes')}>Notificações</Link>
            <Link to="/admin/usuarios" className={getNavClass('/admin/usuarios')}>Usuários</Link>
          </>
        )}
        <Link to="/admin/conta" className={getNavClass('/admin/conta')}>Minha conta</Link>
        <div style={{ flex: 1 }} />
        <button onClick={handleLogout} style={{ padding: '1rem', background: 'transparent', border: '1px solid var(--color-border)', color: '#fff', cursor: 'pointer', borderRadius: '8px' }}>Sair</button>
      </div>

      {/* Main Content */}
      <div className={styles.mainArea}>
        <Routes>
          <Route path="/" element={<Overview user={user} />} />
          <Route path="/conta" element={<Account loginPath="/admin/login" />} />
          {user.role === 'admin' && (
            <>
              <Route path="/loja" element={<AdminStore />} />
              <Route path="/servicos" element={<AdminServices />} />
              <Route path="/barbeiros" element={<AdminBarbers />} />
              <Route path="/financeiro" element={<AdminFinance />} />
              <Route path="/despesas" element={<AdminExpenses />} />
              <Route path="/notificacoes" element={<AdminNotifications />} />
              <Route path="/usuarios" element={<AdminUsers currentUserId={user.id} />} />
            </>
          )}
        </Routes>
      </div>
    </div>
  );
};

export default Dashboard;


