import React, { useState } from 'react';
import { apiErrorMessage } from '../../utils/apiError';
import { validateNewPassword } from '../../utils/profileValidation';
import styles from './Account.module.css';

type Props = {
  /** Troca a senha e devolve a mensagem de confirmação. */
  onChangePassword: (currentPassword: string, newPassword: string) => Promise<string>;
};

const PasswordForm = ({ onChangePassword }: Props) => {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    const problem = validateNewPassword(current, next, confirmation);
    if (problem) {
      setError(problem);
      return;
    }

    setSaving(true);
    try {
      setSuccess(await onChangePassword(current, next));
      setCurrent('');
      setNext('');
      setConfirmation('');
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível trocar a senha.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className={styles.card} onSubmit={handleSubmit} noValidate aria-labelledby="senha-titulo">
      <h2 id="senha-titulo">Trocar senha</h2>

      <div className={styles.field}>
        <label htmlFor="senha-atual">Senha atual</label>
        <input
          id="senha-atual"
          type="password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          autoComplete="current-password"
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="senha-nova">Nova senha</label>
        <input
          id="senha-nova"
          type="password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          autoComplete="new-password"
        />
        <span className={styles.hint}>No mínimo 8 caracteres, com pelo menos 1 letra e 1 número.</span>
      </div>

      <div className={styles.field}>
        <label htmlFor="senha-confirmacao">Confirme a nova senha</label>
        <input
          id="senha-confirmacao"
          type="password"
          value={confirmation}
          onChange={(e) => setConfirmation(e.target.value)}
          autoComplete="new-password"
        />
      </div>

      {error && <p className={styles.error} role="alert">{error}</p>}
      {success && <p className={styles.success} role="status">{success}</p>}

      <div className={styles.actions}>
        <button type="submit" className={styles.submit} disabled={saving}>
          {saving ? 'Trocando...' : 'Trocar senha'}
        </button>
      </div>
    </form>
  );
};

export default PasswordForm;
