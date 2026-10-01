import React, { useState, useEffect } from 'react';
import styles from './AdminShared.module.css';
import api from '../api';

const AdminStore = () => {
  const [products, setProducts] = useState<any[]>([]);

  useEffect(() => {
    api.get('/products').then(res => setProducts(res.data)).catch(console.error);
  }, []);

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
              <td style={{ color: p.stock_quantity < 10 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                {p.stock_quantity} un
              </td>
              <td>{Number(p.price).toFixed(2)}</td>
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

