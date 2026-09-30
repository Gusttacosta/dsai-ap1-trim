import React, { useState } from 'react';
import styles from './AdminShared.module.css';

const AdminFinance = () => {
  const [expenses] = useState([
    { id: 1, desc: 'Conta de Luz', value: 350.00, date: '2026-09-28', status: 'Pago' },
    { id: 2, desc: 'Reposição Pomadas', value: 1200.00, date: '2026-09-29', status: 'Pendente' },
    { id: 3, desc: 'Aluguel', value: 4500.00, date: '2026-10-05', status: 'Pendente' },
  ]);

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>💸 Fluxo de Caixa e Despesas</h2>
        <button className={styles.btnAction}>+ Lançar Despesa</button>
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
          {expenses.map(e => (
            <tr key={e.id}>
              <td style={{ color: '#fff', fontWeight: 500 }}>{e.desc}</td>
              <td>{e.date}</td>
              <td>{e.value.toFixed(2)}</td>
              <td style={{ color: e.status === 'Pago' ? 'var(--color-success)' : 'var(--color-primary)' }}>
                {e.status}
              </td>
              <td>
                <button className={styles.btnIcon}>Editar</button>
                <button className={`${styles.btnIcon} ${styles.btnDanger}`}>Excluir</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AdminFinance;
