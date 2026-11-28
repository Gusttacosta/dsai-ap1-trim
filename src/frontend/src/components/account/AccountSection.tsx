import type { ReactNode } from 'react';
import type { LoadStatus } from '../../hooks/useApiResource';
import styles from './Account.module.css';

// Moldura das seções de "Minha conta" que carregam da API (useApiResource): o título,
// "Carregando...", o erro com "Tentar de novo" e, pronta, o resultado da última ação e o conteúdo.
// Usada por "Meus agendamentos" (SPEC/2026-11-25-meus-agendamentos.md) e por "Trim Club"
// (SPEC/2026-11-26-painel-trim-club.md).

type Props = {
  /** id do título, que dá nome à seção. */
  id: string;
  title: string;
  status: LoadStatus;
  loadError: string;
  reload: () => void;
  /** Resultado da última ação: aviso e erro. */
  notice?: string;
  actionError?: string;
  children: ReactNode;
};

const AccountSection = ({ id, title, status, loadError, reload, notice, actionError, children }: Props) => (
  <section className={styles.card} aria-labelledby={id}>
    <h2 id={id}>{title}</h2>

    {status === 'loading' && <p>Carregando...</p>}
    {status === 'error' && (
      <>
        <p className={styles.error} role="alert">
          {loadError}
        </p>
        <div className={styles.actions}>
          <button type="button" className={styles.submit} onClick={reload}>
            Tentar de novo
          </button>
        </div>
      </>
    )}

    {status === 'ready' && (
      <>
        {actionError && (
          <p className={styles.error} role="alert">
            {actionError}
          </p>
        )}
        {notice && (
          <p className={styles.success} role="status">
            {notice}
          </p>
        )}
        {children}
      </>
    )}
  </section>
);

export default AccountSection;
