import shared from '../../pages/AdminShared.module.css';
import { StatusBadge } from '../AdminForm';
import ConfirmButton from '../ConfirmButton';
import type { AdminUser } from '../../hooks/useAdminUsers';
import { ROLE_LABELS, ROLES, type UserRole } from '../../utils/roles';
import styles from '../services/Services.module.css';

// Uma linha da tabela de usuários do painel (SPEC/2026-11-25-admin-usuarios.md). Desativar e
// gerar a senha temporária pedem confirmação na própria linha (ConfirmButton); ativar não pede.
// Na linha do próprio admin não há ações: o backend recusaria.

type Props = {
  user: AdminUser;
  /** A linha é a do admin logado. */
  isSelf: boolean;
  /** Uma ação desta linha está em andamento: os controles ficam desabilitados. */
  busy: boolean;
  onChangeRole: (user: AdminUser, role: UserRole) => void;
  onSetActive: (user: AdminUser, isActive: boolean) => void;
  onGeneratePassword: (user: AdminUser) => void;
};

const UserActions = ({ user, busy, onSetActive, onGeneratePassword }: Omit<Props, 'isSelf' | 'onChangeRole'>) => {
  if (!user.is_active) {
    return (
      <button className={shared.btnIcon} onClick={() => onSetActive(user, true)} disabled={busy}>
        Ativar
      </button>
    );
  }
  return (
    <>
      <ConfirmButton
        label="Gerar senha temporária"
        question="Gerar uma senha temporária? A atual deixa de valer."
        onConfirm={() => onGeneratePassword(user)}
        busy={busy}
      />
      <ConfirmButton label="Desativar" question="Desativar esta conta?" onConfirm={() => onSetActive(user, false)} busy={busy} />
    </>
  );
};

const UserRow = ({ user, isSelf, busy, onChangeRole, onSetActive, onGeneratePassword }: Props) => (
  <tr className={user.is_active ? undefined : styles.inactive} aria-label={user.full_name}>
    <td style={{ color: '#fff', fontWeight: 500 }}>
      {user.full_name}
      <span className={styles.description}>{user.email}</span>
    </td>
    <td>
      {isSelf ? (
        ROLE_LABELS[user.role]
      ) : (
        <select
          aria-label={`Perfil de ${user.full_name}`}
          value={user.role}
          onChange={(e) => onChangeRole(user, e.target.value as UserRole)}
          disabled={busy}
        >
          {ROLES.map((role) => (
            <option key={role} value={role}>{ROLE_LABELS[role]}</option>
          ))}
        </select>
      )}
    </td>
    <td>
      <StatusBadge active={user.is_active} />
      {user.must_change_password && <span className={styles.description}>Troca de senha pendente</span>}
    </td>
    <td>
      {isSelf ? (
        <span className={styles.description}>Você</span>
      ) : (
        <UserActions user={user} busy={busy} onSetActive={onSetActive} onGeneratePassword={onGeneratePassword} />
      )}
    </td>
  </tr>
);

export default UserRow;
