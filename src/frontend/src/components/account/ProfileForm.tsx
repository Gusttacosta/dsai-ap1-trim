import React, { useEffect, useRef, useState } from 'react';
import type { AccountUser, ProfileChanges } from '../../hooks/useAccount';
import { apiErrorMessage } from '../../utils/apiError';
import { formatPhone, validateAvatarUrl, validateFullName, validatePhone } from '../../utils/profileValidation';
import styles from './Account.module.css';

type Props = {
  user: AccountUser;
  /** Salva e devolve o usuário como o backend gravou. */
  onSave: (changes: ProfileChanges) => Promise<AccountUser | void>;
};

/** Campos alterados em relação ao usuário salvo, já no formato do backend. */
export function profileChanges(
  user: AccountUser,
  form: { fullName: string; phone: string; avatarUrl: string },
): ProfileChanges {
  const changes: ProfileChanges = {};
  const fullName = form.fullName.trim();
  const phone = formatPhone(form.phone) || null;
  const avatarUrl = form.avatarUrl.trim() || null;
  if (fullName !== user.full_name) changes.full_name = fullName;
  if (phone !== user.phone) changes.phone = phone;
  if (avatarUrl !== user.avatar_url) changes.avatar_url = avatarUrl;
  return changes;
}

const ProfileForm = ({ user, onSave }: Props) => {
  const [fullName, setFullName] = useState(user.full_name);
  const [phone, setPhone] = useState(user.phone ?? '');
  const [avatarUrl, setAvatarUrl] = useState(user.avatar_url ?? '');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);

  const showSaved = (saved: AccountUser) => {
    setFullName(saved.full_name);
    setPhone(saved.phone ?? '');
    setAvatarUrl(saved.avatar_url ?? '');
  };

  // Quando o usuário muda depois da montagem, os campos acompanham. Na montagem os campos já
  // começam com ele: rodar aqui apagaria o que a pessoa digitou antes de o efeito rodar.
  const shownUser = useRef(user);
  useEffect(() => {
    if (shownUser.current === user) return;
    shownUser.current = user;
    showSaved(user);
  }, [user]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    const problem = validateFullName(fullName) ?? validatePhone(phone) ?? validateAvatarUrl(avatarUrl);
    if (problem) {
      setError(problem);
      return;
    }
    const changes = profileChanges(user, { fullName, phone, avatarUrl });
    if (Object.keys(changes).length === 0) {
      setSuccess('Nada mudou desde o último salvamento.');
      return;
    }

    setSaving(true);
    try {
      const saved = await onSave(changes);
      // Mostra o que o backend gravou (o telefone volta normalizado) junto com a confirmação,
      // sem esperar o efeito acima, que roda depois da renderização.
      if (saved) showSaved(saved);
      setSuccess('Dados salvos.');
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível salvar seus dados.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className={styles.card} onSubmit={handleSubmit} noValidate aria-labelledby="perfil-titulo">
      <h2 id="perfil-titulo">Dados pessoais</h2>

      <div className={styles.field}>
        <label htmlFor="perfil-nome">Nome</label>
        <input
          id="perfil-nome"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          autoComplete="name"
          maxLength={255}
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="perfil-telefone">Telefone</label>
        <input
          id="perfil-telefone"
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          autoComplete="tel-national"
          placeholder="(91) 99999-0000"
        />
        <span className={styles.hint}>Com DDD. Deixe em branco para remover.</span>
      </div>

      <div className={styles.field}>
        <label htmlFor="perfil-foto">URL da foto</label>
        <input
          id="perfil-foto"
          type="url"
          value={avatarUrl}
          onChange={(e) => setAvatarUrl(e.target.value)}
          placeholder="https://"
        />
      </div>

      {error && <p className={styles.error} role="alert">{error}</p>}
      {success && <p className={styles.success} role="status">{success}</p>}

      <div className={styles.actions}>
        <button type="submit" className={styles.submit} disabled={saving}>
          {saving ? 'Salvando...' : 'Salvar dados'}
        </button>
      </div>
    </form>
  );
};

export default ProfileForm;
