import { Navigate } from 'react-router-dom';
import PasswordForm from '../components/account/PasswordForm';
import ProfileForm from '../components/account/ProfileForm';
import styles from '../components/account/Account.module.css';
import { useAccount, type AccountUser } from '../hooks/useAccount';

// "Minha conta": dados pessoais e troca de senha (SPEC/2026-11-22-auth-perfil-senha.md).
// Serve ao cliente em /conta e ao admin e ao barbeiro em /admin/conta.

type Props = {
  /** Para onde mandar quem não está logado. */
  loginPath: string;
};

const ROLE_LABELS: Record<AccountUser['role'], string> = {
  admin: 'Administrador',
  barber: 'Barbeiro',
  client: 'Cliente',
};

const Avatar = ({ user }: { user: AccountUser }) =>
  user.avatar_url ? (
    <img className={styles.avatar} src={user.avatar_url} alt="" />
  ) : (
    <div className={styles.avatar} aria-hidden="true">
      {user.full_name.trim().charAt(0).toUpperCase()}
    </div>
  );

const Account = ({ loginPath }: Props) => {
  const { user, status, loadError, saveProfile, changePassword } = useAccount();

  if (status === 'unauthenticated') return <Navigate to={loginPath} replace />;
  if (status === 'loading') return <p className={styles.page}>Carregando...</p>;
  if (status === 'error' || !user) {
    return (
      <p className={`${styles.page} ${styles.error}`} role="alert">
        {loadError}
      </p>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Avatar user={user} />
        <div className={styles.identity}>
          <h1>Minha conta</h1>
          <p className={styles.email}>
            {user.email} · {ROLE_LABELS[user.role]}
          </p>
        </div>
      </header>

      {!user.email_verified && (
        <p className={styles.warning}>Seu e-mail ainda não foi verificado.</p>
      )}

      <ProfileForm user={user} onSave={saveProfile} />
      <PasswordForm onChangePassword={changePassword} />
    </div>
  );
};

export default Account;
