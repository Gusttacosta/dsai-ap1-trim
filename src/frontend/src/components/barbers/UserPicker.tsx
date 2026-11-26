import { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import LoadState from '../LoadState';
import Pagination from '../Pagination';
import UserFilters from '../users/UserFilters';
import { useAdminUsers, type AdminUser } from '../../hooks/useAdminUsers';
import styles from '../services/Services.module.css';

// Primeiro passo de "Novo barbeiro": achar o usuário com a mesma busca e a mesma paginação da aba
// Usuários (SPEC/2026-11-26-painel-barbeiros.md). Quem já é barbeiro não pode ser escolhido.

type Props = {
  /** Ids dos usuários que já têm perfil de barbeiro. */
  barberUserIds: Set<string>;
  onPick: (user: AdminUser) => void;
  onCancel: () => void;
};

const UserPicker = ({ barberUserIds, onPick, onCancel }: Props) => {
  const [filters, setFilters] = useState({ q: '', role: '' as const, page: 1 });
  const { users, page, total_pages, status, loadError, reload } = useAdminUsers(filters);

  return (
    <section className={styles.form} aria-label="Escolher o usuário">
      <h3>Novo barbeiro: escolha o usuário</h3>

      <div className={styles.wide}>
        <UserFilters onSearch={(q) => setFilters({ q, role: '', page: 1 })} />
        <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando usuários...">
          {users.length === 0 ? (
            <p>Nenhum usuário encontrado.</p>
          ) : (
            <table className={shared.table}>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} aria-label={user.full_name}>
                    <td>
                      {user.full_name}
                      <span className={styles.description}>{user.email}</span>
                    </td>
                    <td>
                      {barberUserIds.has(user.id) ? (
                        <span className={styles.description}>Já é barbeiro</span>
                      ) : (
                        <button type="button" className={shared.btnIcon} onClick={() => onPick(user)}>
                          Escolher
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <Pagination page={page} totalPages={total_pages} onChange={(p) => setFilters((f) => ({ ...f, page: p }))} />
        </LoadState>
      </div>

      <div className={styles.actions}>
        <button type="button" className={styles.secondary} onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </section>
  );
};

export default UserPicker;
