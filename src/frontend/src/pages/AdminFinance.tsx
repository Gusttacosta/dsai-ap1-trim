import React, { useState, useEffect } from 'react';
import styles from './AdminShared.module.css';
import api from '../api';

const AdminFinance = () => {
  const [expenses, setExpenses] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>({ total_revenue: 0, total_expenses: 0, net_profit: 0 });

  useEffect(() => {
    // Busca dados financeiros reais do backend
    api.get('/reports/financial-summary').then(res => {
      setSummary(res.data);
      // Aqui idealmente teríamos uma rota de listagem de despesas,
      // mas vamos usar o summary por enquanto para mostrar valores agregados.
    }).catch(console.error);
    
    // Supondo que você criou uma rota para buscar despesas
    // api.get('/expenses').then(res => setExpenses(res.data));
  }, []);

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>💸 Fluxo de Caixa e Despesas</h2>
        <button className={styles.btnAction}>+ Lançar Despesa</button>
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

      <table className={styles.table}>
        <thead>
          <tr>
            <th>Descrição</th>
            <th>Data</th>
            <th>Valor (R$)</th>
            <th>Status</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {expenses.length === 0 ? (
            <tr>
              <td colSpan={5} style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>
                Buscando despesas na API... (Você pode criar a rota GET /expenses depois)
              </td>
            </tr>
          ) : (
            expenses.map(e => (
              <tr key={e.id}>
                <td style={{ color: '#fff', fontWeight: 500 }}>{e.description}</td>
                <td>{e.date}</td>
                <td>{Number(e.amount).toFixed(2)}</td>
                <td style={{ color: 'var(--color-success)' }}>Pago</td>
                <td>
                  <button className={styles.btnIcon}>Editar</button>
                  <button className={`${styles.btnIcon} ${styles.btnDanger}`}>Excluir</button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default AdminFinance;


