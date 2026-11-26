import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import styles from './AdminShared.module.css';
import api from '../api';

// A lista de despesas fica na aba Despesas (SPEC/2026-11-26-painel-despesas.md).
const AdminFinance = () => {
  const [summary, setSummary] = useState<any>({ total_revenue: 0, total_expenses: 0, net_profit: 0 });

  useEffect(() => {
    // Busca dados financeiros reais do backend
    api.get('/reports/financial-summary').then(res => {
      setSummary(res.data);
    }).catch(console.error);
  }, []);

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>💸 Fluxo de Caixa e Despesas</h2>
      </div>

      <div style={{ display: 'flex', gap: '2rem', marginBottom: '2rem' }}>
        <div style={{ padding: '1.5rem', background: 'var(--color-bg-card)', borderRadius: '12px', flex: 1, border: '1px solid var(--color-border)' }}>
          <h3 style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>Receita Total (Mês)</h3>
          <p style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--color-success)' }}>R$ {Number(summary.total_revenue).toFixed(2)}</p>
        </div>
        <div style={{ padding: '1.5rem', background: 'var(--color-bg-card)', borderRadius: '12px', flex: 1, border: '1px solid var(--color-border)' }}>
          <h3 style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>Despesas (Mês)</h3>
          <p style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--color-primary)' }}>R$ {Number(summary.total_expenses).toFixed(2)}</p>
        </div>
        <div style={{ padding: '1.5rem', background: 'var(--color-bg-card)', borderRadius: '12px', flex: 1, border: '1px solid var(--color-border)' }}>
          <h3 style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>Lucro Líquido</h3>
          <p style={{ fontSize: '1.8rem', fontWeight: 700, color: '#fff' }}>R$ {Number(summary.net_profit).toFixed(2)}</p>
        </div>
      </div>

      <p>
        As despesas são lançadas e corrigidas na aba{' '}
        <Link to="/admin/despesas" className={styles.btnIcon}>Gerenciar despesas</Link>
      </p>
    </div>
  );
};

export default AdminFinance;


