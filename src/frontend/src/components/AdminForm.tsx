import React, { useState, type ReactNode } from 'react';
import { apiErrorMessage } from '../utils/apiError';
import styles from './services/Services.module.css';

// Moldura dos formulários do painel do admin: título, erro, "Nada mudou.", "Salvando..." e
// "Cancelar". Usada pelos formulários de serviço (SPEC/2026-11-23-painel-servicos.md) e de
// barbeiro (SPEC/2026-11-26-painel-barbeiros.md). Quem usa cuida só dos campos.

type Props = {
  title: string;
  /** Texto do botão de salvar. Enquanto salva, vira "Salvando...". */
  submitLabel: string;
  /** Mensagem quando a API falha sem dizer o motivo. */
  errorFallback: string;
  /** Confere os campos antes da API: a mensagem do problema, ou null. */
  validate: () => string | null;
  /**
   * Grava. Devolve false quando não havia nada para gravar (o formulário diz "Nada mudou.").
   * Quem chamou fecha o formulário depois de salvar.
   */
  save: () => Promise<boolean>;
  onCancel: () => void;
  children: ReactNode;
};

const AdminForm = ({ title, submitLabel, errorFallback, validate, save, onCancel, children }: Props) => {
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setInfo('');

    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }

    setSaving(true);
    try {
      if (!(await save())) {
        setInfo('Nada mudou.');
        setSaving(false);
      }
    } catch (err) {
      setError(apiErrorMessage(err, errorFallback));
      setSaving(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate aria-label={title}>
      <h3>{title}</h3>

      {children}

      {error && <p className={styles.error} role="alert">{error}</p>}
      {info && <p className={styles.info} role="status">{info}</p>}

      <div className={styles.actions}>
        <button type="button" className={styles.secondary} onClick={onCancel} disabled={saving}>
          Cancelar
        </button>
        <button type="submit" className={styles.primary} disabled={saving}>
          {saving ? 'Salvando...' : submitLabel}
        </button>
      </div>
    </form>
  );
};

/** Um campo do formulário: rótulo e controle, em meia linha ou na linha inteira (`wide`). */
export const FormField = ({ id, label, wide = false, children }: {
  id: string;
  label: string;
  wide?: boolean;
  children: ReactNode;
}) => (
  <div className={wide ? `${styles.field} ${styles.wide}` : styles.field}>
    <label htmlFor={id}>{label}</label>
    {children}
  </div>
);

/** Selo de situação das linhas do painel: "Ativo" ou "Desativado". */
export const StatusBadge = ({ active }: { active: boolean }) => (
  <span className={`${styles.badge} ${active ? styles.badgeActive : styles.badgeInactive}`}>
    {active ? 'Ativo' : 'Desativado'}
  </span>
);

export default AdminForm;
