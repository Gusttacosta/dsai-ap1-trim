import type { ReactNode } from 'react';
import type { LoadStatus } from '../hooks/useApiResource';
import shared from '../pages/AdminShared.module.css';
import styles from './services/Services.module.css';

// Estado da carga de uma tela do painel (useApiResource): "carregando", o erro com "Tentar de
// novo", ou o conteúdo. E as mensagens do resultado de uma ação (useRowAction). Usado pelos
// painéis de serviços e de usuários (SPEC/2026-11-25-admin-usuarios.md).

type Props = {
  status: LoadStatus;
  loadError: string;
  reload: () => void;
  /** Texto enquanto carrega. */
  loadingText: string;
  children: ReactNode;
};

const LoadState = ({ status, loadError, reload, loadingText, children }: Props) => {
  if (status === 'loading') return <p>{loadingText}</p>;
  if (status === 'error') {
    return (
      <div>
        <p className={styles.error} role="alert">{loadError}</p>
        <button className={shared.btnAction} onClick={reload}>Tentar de novo</button>
      </div>
    );
  }
  return <>{children}</>;
};

/** Mensagem de sucesso e erro de uma ação, no topo da tela. */
export const ActionFeedback = ({ message, error }: { message: string; error: string }) => (
  <>
    {message && <p className={styles.info} role="status">{message}</p>}
    {error && <p className={styles.error} role="alert">{error}</p>}
  </>
);

export default LoadState;
