import React, { useState, useEffect } from 'react';
import styles from './AdminShared.module.css';
import api from '../api';

const AdminServices = () => {
  const [services, setServices] = useState<any[]>([]);

  useEffect(() => {
    api.get('/services').then(res => setServices(res.data)).catch(console.error);
  }, []);

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>✂️ Gestão de Serviços</h2>
        <button className={styles.btnAction}>+ Novo Serviço</button>
      </div>

      <table className={styles.table}>
        <thead>
          <tr>
            <th>Serviço</th>
            <th>Duração (min)</th>
            <th>Preço (R$)</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {services.map(s => (
            <tr key={s.id}>
              <td style={{ color: '#fff', fontWeight: 500 }}>{s.name}</td>
              <td>{s.duration_minutes} min</td>
              <td>{s.price.toFixed(2)}</td>
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

export default AdminServices;
