import { useCallback, useEffect, useState } from 'react';
import api from '../../api';
import { apiErrorMessage } from '../../utils/apiError';
import styles from './Account.module.css';

// Notificações do usuário logado em "Minha conta" (SPEC/2026-11-25-notificacoes.md, #75).

export type AppNotification = {
  id: string;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
};

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });

const NotificationsList = () => {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const response = await api.get<AppNotification[]>('/notifications');
      setItems(Array.isArray(response.data) ? response.data : []);
      setError('');
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível carregar as notificações.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const act = async (action: () => Promise<unknown>, fallback: string) => {
    try {
      await action();
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, fallback));
    }
  };

  const unread = items.filter((n) => !n.is_read).length;

  return (
    <section className={styles.card} aria-labelledby="notificacoes-titulo">
      <h2 id="notificacoes-titulo">
        Notificações{unread > 0 && ` (${unread} não ${unread === 1 ? 'lida' : 'lidas'})`}
      </h2>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {loading && <p>Carregando...</p>}
      {!loading && !error && items.length === 0 && <p className={styles.hint}>Nenhuma notificação por aqui.</p>}

      {items.length > 0 && (
        <>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {items.map((n) => (
              <li
                key={n.id}
                data-testid="notificacao"
                style={{ padding: '0.75rem 0', borderBottom: '1px solid var(--color-border)', opacity: n.is_read ? 0.6 : 1 }}
              >
                <strong>{n.title}</strong> <span className={styles.hint}>{formatDate(n.created_at)}</span>
                <p style={{ margin: '0.25rem 0' }}>{n.message}</p>
                {!n.is_read && (
                  <button
                    type="button"
                    onClick={() => act(() => api.put(`/notifications/${n.id}/read`), 'Não foi possível marcar como lida.')}
                  >
                    Marcar como lida
                  </button>
                )}{' '}
                <button
                  type="button"
                  aria-label={`Apagar ${n.title}`}
                  onClick={() => act(() => api.delete(`/notifications/${n.id}`), 'Não foi possível apagar.')}
                >
                  Apagar
                </button>
              </li>
            ))}
          </ul>
          {unread > 0 && (
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.submit}
                onClick={() => act(() => api.put('/notifications/read-all'), 'Não foi possível marcar todas.')}
              >
                Marcar todas como lidas
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
};

export default NotificationsList;
