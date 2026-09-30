import React, { useState } from 'react';
import styles from './AdminShared.module.css';

const AdminServices = () => {
  const [services] = useState([
    { id: 1, name: 'Corte Máquina', duration: 30, price: 40.00 },
    { id: 2, name: 'Corte + Barba', duration: 60, price: 75.00 },
    { id: 3, name: 'Platinado', duration: 120, price: 120.00 },
  ]);

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
              <td>{s.duration} min</td>
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
