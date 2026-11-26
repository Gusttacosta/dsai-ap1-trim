import { Navigate, useNavigate } from 'react-router-dom';
import PasswordForm from '../components/account/PasswordForm';
import styles from '../components/account/Account.module.css';
import { useAccount } from '../hooks/useAccount';
import { homeFor } from '../utils/afterLogin';

// Troca obrigatória da senha temporária gerada pelo admin (SPEC/2026-11-25-admin-usuarios.md).
// Até a troca, a API só responde ao perfil e à troca de senha. Trocada, a pessoa segue para a
// área do seu perfil.

const ChangePasswordRequired = () => {
  const { user, status, loadError, changePassword } = useAccount();
  const navigate = useNavigate();

  if (status === 'unauthenticated') return <Navigate to="/login" replace />;
  if (status === 'loading') return <p className={styles.page}>Carregando...</p>;
  if (status === 'error' || !user) {
    return (
      <p className={`${styles.page} ${styles.error}`} role="alert">
        {loadError}
      </p>
    );
  }
  if (!user.must_change_password) return <Navigate to={homeFor(user.role)} replace />;

  const change = async (current: string, next: string) => {
    const message = await changePassword(current, next);
    navigate(homeFor(user.role), { replace: true });
    return message;
  };

  return (
    <div className={styles.page}>
      <header className={styles.identity}>
        <h1>Troque sua senha</h1>
      </header>
      <p className={styles.warning}>
        Você entrou com uma senha temporária. Para continuar, escolha uma senha nova. Em "Senha
        atual", use a senha temporária.
      </p>
      <PasswordForm onChangePassword={change} />
    </div>
  );
};

export default ChangePasswordRequired;
