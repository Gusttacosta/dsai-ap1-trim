import React, { useState } from 'react';
import styles from './AdminShared.module.css';

const AdminStore = () => {
  const [products] = useState([
    { id: 1, name: 'Pomada Efeito Matte Trim', stock: 42, price: 55.00 },
    { id: 2, name: 'Óleo para Barba Premium', stock: 15, price: 89.90 },
    { id: 3, name: 'Balm Refrescante', stock: 8, price: 45.00 },
  ]);

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>📦 Controle de Estoque (Loja)</h2>
        <button className={styles.btnAction}>+ Novo Produto</button>
      </div>

      <table className={styles.table}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Produto</th>
            <th>Estoque</th>
            <th>Preço (R$)</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {products.map(p => (
            <tr key={p.id}>
              <td>#{p.id}</td>
              <td style={{ color: '#fff', fontWeight: 500 }}>{p.name}</td>
              <td style={{ color: p.stock < 10 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                {p.stock} un
              </td>
              <td>{p.price.toFixed(2)}</td>
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

export default AdminStore;
