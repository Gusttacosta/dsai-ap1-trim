import type { ReactElement } from 'react';
import { Navigate } from 'react-router-dom';
import type { AccountStatus } from '../../hooks/useAccount';
import styles from './Account.module.css';

// O que as telas da própria conta mostram enquanto ela não está pronta: o login para quem não
// está logado, "Carregando..." ou o erro. Usado por "Minha conta" e pela troca obrigatória de
// senha (SPEC/2026-11-25-admin-usuarios.md).

type Account = { user: unknown; status: AccountStatus; loadError: string };

/** O elemento a mostrar no lugar da tela, ou null quando a conta está pronta. */
export function accountFallback({ user, status, loadError }: Account, loginPath: string): ReactElement | null {
  if (status === 'unauthenticated') return <Navigate to={loginPath} replace />;
  if (status === 'loading') return <p className={styles.page}>Carregando...</p>;
  if (status === 'error' || !user) {
    return (
      <p className={`${styles.page} ${styles.error}`} role="alert">
        {loadError}
      </p>
    );
  }
  return null;
}
