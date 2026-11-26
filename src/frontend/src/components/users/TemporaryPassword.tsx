import { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import styles from '../account/Account.module.css';

// A senha temporária recém-gerada, mostrada uma única vez (SPEC/2026-11-25-admin-usuarios.md).
// "Fechar" tira a senha da tela: quem a mostra não a guarda em outro lugar.

type Props = {
  userName: string;
  password: string;
  onClose: () => void;
};

const TemporaryPassword = ({ userName, password, onClose }: Props) => {
  const [copyStatus, setCopyStatus] = useState<'' | 'copied' | 'failed'>('');

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(password);
      setCopyStatus('copied');
    } catch {
      setCopyStatus('failed');
    }
  };

  return (
    <section className={styles.card} aria-labelledby="senha-temporaria-titulo">
      <h2 id="senha-temporaria-titulo">Senha temporária de {userName}</h2>
      <p className={styles.hint}>
        Ela não será mostrada de novo. Entregue-a à pessoa: no próximo login, ela vai precisar trocá-la.
      </p>
      <code className={shared.secret} aria-label="Senha temporária">{password}</code>
      {copyStatus === 'copied' && <p className={styles.success} role="status">Senha copiada.</p>}
      {copyStatus === 'failed' && (
        <p className={styles.error} role="alert">Não foi possível copiar. Selecione a senha e copie à mão.</p>
      )}
      <div className={styles.actions}>
        <button type="button" className={shared.btnIcon} onClick={copy}>Copiar</button>
        <button type="button" className={styles.submit} onClick={onClose}>Fechar</button>
      </div>
    </section>
  );
};

export default TemporaryPassword;
