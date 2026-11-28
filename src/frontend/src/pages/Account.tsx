import { Navigate } from 'react-router-dom';
import { accountFallback } from '../components/account/accountFallback';
import MyAppointments from '../components/account/MyAppointments';
import MySubscription from '../components/account/MySubscription';
import NotificationsList from '../components/account/NotificationsList';
import PasswordForm from '../components/account/PasswordForm';
import ProfileForm from '../components/account/ProfileForm';
import styles from '../components/account/Account.module.css';
import { useAccount, type AccountUser } from '../hooks/useAccount';
import { CHANGE_PASSWORD_PATH } from '../utils/afterLogin';
import { ROLE_LABELS } from '../utils/roles';

// "Minha conta": dados pessoais e troca de senha (SPEC/2026-11-22-auth-perfil-senha.md).
// Serve ao cliente em /conta e ao admin e ao barbeiro em /admin/conta. Só o cliente vê
// "Meus agendamentos" (SPEC/2026-11-25-meus-agendamentos.md) e a assinatura do Trim Club
// (SPEC/2026-11-26-painel-trim-club.md).

type Props = {
  /** Para onde mandar quem não está logado. */
  loginPath: string;
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
  const account = useAccount();
  const { user, saveProfile, changePassword } = account;

  const fallback = accountFallback(account, loginPath);
  if (fallback || !user) return fallback;
  if (user.must_change_password) return <Navigate to={CHANGE_PASSWORD_PATH} replace />;

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

      {user.role === 'client' && (
        <>
          <MySubscription />
          <MyAppointments />
        </>
      )}
      <ProfileForm user={user} onSave={saveProfile} />
      <PasswordForm onChangePassword={changePassword} />
      <NotificationsList />
    </div>
  );
};

export default Account;
