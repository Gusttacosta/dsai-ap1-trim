import React, { useState } from 'react';
import api from '../api';
import { apiErrorMessage } from '../utils/apiError';
import styles from './AdminShared.module.css';

// Aviso geral do admin (SPEC/2026-11-25-notificacoes.md, #75). Antes, a tela só mostrava um
// alert() e nada era enviado.

const AUDIENCES = [
  { value: 'all', label: 'Todos' },
  { value: 'clients', label: 'Clientes' },
  { value: 'barbers', label: 'Barbeiros' },
  { value: 'admins', label: 'Administradores' },
] as const;

type Audience = (typeof AUDIENCES)[number]['value'];

const fieldStyle: React.CSSProperties = {
  width: '100%', background: 'var(--color-bg)', border: '1px solid var(--color-border)', color: '#fff',
  padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem',
};

const AdminNotifications = () => {
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [audience, setAudience] = useState<Audience>('all');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');

  const ready = title.trim() !== '' && message.trim() !== '' && !sending;

  const handleSend = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    setSending(true);
    setResult('');
    setError('');
    try {
      const response = await api.post<{ detail: string }>('/notifications/broadcast', {
        title: title.trim(),
        message: message.trim(),
        audience,
      });
      setResult(response.data.detail);
      setTitle('');
      setMessage('');
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível enviar o aviso.'));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>🔔 Avisos para os usuários</h2>
      </div>

      <form
        onSubmit={handleSend}
        style={{ background: 'var(--color-bg-elevated)', padding: '2rem', borderRadius: 'var(--radius-lg)' }}
      >
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem' }}>
          O aviso aparece em "Minha conta" de cada usuário ativo do público escolhido.
        </p>

        <label htmlFor="aviso-publico">Público</label>
        <select
          id="aviso-publico"
          style={fieldStyle}
          value={audience}
          onChange={(e) => setAudience(e.target.value as Audience)}
        >
          {AUDIENCES.map((a) => (
            <option key={a.value} value={a.value}>
              {a.label}
            </option>
          ))}
        </select>

        <label htmlFor="aviso-titulo">Título</label>
        <input
          id="aviso-titulo"
          style={fieldStyle}
          maxLength={150}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ex: Feriado na sexta-feira"
        />

        <label htmlFor="aviso-mensagem">Mensagem</label>
        <textarea
          id="aviso-mensagem"
          style={{ ...fieldStyle, minHeight: '120px' }}
          maxLength={2000}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ex: Estaremos fechados na sexta. Garanta seu horário na quinta!"
        />

        {result && <p role="status">{result}</p>}
        {error && <p role="alert" style={{ color: 'var(--color-error, #f87171)' }}>{error}</p>}

        <div style={{ textAlign: 'right' }}>
          <button type="submit" className={styles.btnAction} disabled={!ready} style={{ opacity: ready ? 1 : 0.5 }}>
            {sending ? 'Enviando...' : 'Enviar aviso'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AdminNotifications;
