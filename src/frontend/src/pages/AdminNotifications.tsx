import React, { useState } from 'react';
import styles from './AdminShared.module.css';

const AdminNotifications = () => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    alert(`Notificação enviada em massa: "${message}"`);
    setMessage('');
  };

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>🔔 Disparo de Notificações</h2>
      </div>

      <div style={{ background: 'var(--color-bg-elevated)', padding: '2rem', borderRadius: 'var(--radius-lg)' }}>
        <h3 style={{ marginBottom: '1rem', color: '#fff' }}>Nova Campanha</h3>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem' }}>
          Escreva uma mensagem para notificar todos os clientes cadastrados no App via Push Notification.
        </p>
        
        <textarea 
          style={{ 
            width: '100%', minHeight: '120px', background: 'var(--color-bg)', 
            border: '1px solid var(--color-border)', color: '#fff', 
            padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem' 
          }}
          placeholder="Ex: Feriadão chegando! Garanta seu horário com 10% OFF usando o cupom TRIM10..."
          value={message}
          onChange={e => setMessage(e.target.value)}
        />
        
        <div style={{ textAlign: 'right' }}>
          <button 
            className={styles.btnAction} 
            disabled={!message}
            onClick={handleSend}
            style={{ opacity: !message ? 0.5 : 1 }}
          >
            Disparar Push Notification
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminNotifications;
