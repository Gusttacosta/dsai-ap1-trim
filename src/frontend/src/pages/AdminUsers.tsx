import { useState } from 'react';
import styles from './AdminShared.module.css';
import LoadState, { ActionFeedback } from '../components/LoadState';
import Pagination from '../components/Pagination';
import TemporaryPassword from '../components/users/TemporaryPassword';
import UserFilters from '../components/users/UserFilters';
import UserRow from '../components/users/UserRow';
import { useAdminUsers, type AdminUser, type UserFilters as Filters } from '../hooks/useAdminUsers';
import { useRowAction } from '../hooks/useRowAction';
import { ROLE_LABELS, type UserRole } from '../utils/roles';

// Usuários no painel do admin: lista, busca, perfil, ativar e desativar, e a senha temporária
// (SPEC/2026-11-25-admin-usuarios.md).

type Props = {
  /** Id do admin logado: a linha dele não tem ações. */
  currentUserId: string;
};

const AdminUsers = ({ currentUserId }: Props) => {
  const [filters, setFilters] = useState<Filters>({ q: '', role: '', page: 1 });
  const { users, total, page, total_pages, status, loadError, reload, changeRole, setActive, generateTemporaryPassword } =
    useAdminUsers(filters);
  const { busyId, message, actionError, run } = useRowAction();
  // A senha só existe aqui, até o admin fechar o quadro ou sair da tela.
  const [generated, setGenerated] = useState<{ name: string; password: string } | null>(null);

  /** Busca ou filtro novo volta para a primeira página. */
  const filter = (changes: Partial<Filters>) => setFilters((current) => ({ ...current, ...changes, page: 1 }));

  const onChangeRole = (user: AdminUser, role: UserRole) =>
    run(user.id, () => changeRole(user.id, role), `${user.full_name} agora é ${ROLE_LABELS[role]}.`);

  const onSetActive = (user: AdminUser, isActive: boolean) =>
    run(user.id, () => setActive(user.id, isActive), isActive ? 'Conta ativada.' : 'Conta desativada.');

  const onGeneratePassword = async (user: AdminUser) => {
    setGenerated(null);
    const password = await run(user.id, () => generateTemporaryPassword(user.id), 'Senha temporária gerada.');
    if (password) setGenerated({ name: user.full_name, password });
  };

  return (
    <div className={styles.adminContainer}>
      <div className={styles.header}>
        <h2 className={styles.title}>👥 Usuários</h2>
        {status === 'ready' && <span>{total} {total === 1 ? 'usuário' : 'usuários'}</span>}
      </div>

      {generated && (
        <TemporaryPassword userName={generated.name} password={generated.password} onClose={() => setGenerated(null)} />
      )}

      <ActionFeedback message={message} error={actionError} />

      <UserFilters role={filters.role} onSearch={(q) => filter({ q })} onRoleChange={(role) => filter({ role })} />

      <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando usuários...">
        {users.length === 0 ? (
          <p>Nenhum usuário encontrado.</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Usuário</th>
                <th>Perfil</th>
                <th>Situação</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <UserRow
                  key={user.id}
                  user={user}
                  isSelf={user.id === currentUserId}
                  busy={busyId === user.id}
                  onChangeRole={onChangeRole}
                  onSetActive={onSetActive}
                  onGeneratePassword={onGeneratePassword}
                />
              ))}
            </tbody>
          </table>
        )}
        <Pagination page={page} totalPages={total_pages} onChange={(p) => setFilters((f) => ({ ...f, page: p }))} />
      </LoadState>
    </div>
  );
};

export default AdminUsers;
