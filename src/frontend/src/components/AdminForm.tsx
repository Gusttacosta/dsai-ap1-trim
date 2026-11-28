import React, { useState, type ReactNode } from 'react';
import { apiErrorMessage } from '../utils/apiError';
import styles from './services/Services.module.css';

// Moldura dos formulários do painel do admin: título, erro, "Nada mudou.", "Salvando..." e
// "Cancelar". Usada pelos formulários de serviço (SPEC/2026-11-23-painel-servicos.md) e de
// barbeiro (SPEC/2026-11-26-painel-barbeiros.md). Quem usa cuida só dos campos. Com `confirm`, pede
// confirmação antes de gravar (o ajuste de pontos, SPEC/2026-11-26-painel-fidelidade.md).

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
  /**
   * Pergunta mostrada, com os campos já válidos, antes de gravar: "Confirmar" grava e "Voltar"
   * (ou mudar um campo) volta ao formulário. Sem ela, grava direto.
   */
  confirm?: () => string;
  children: ReactNode;
};

const AdminForm = ({ title, submitLabel, errorFallback, validate, save, onCancel, confirm, children }: Props) => {
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [saving, setSaving] = useState(false);
  // A pergunta de `confirm` enquanto espera a resposta; null fora da confirmação.
  const [question, setQuestion] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setInfo('');

    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }
    if (confirm && question === null) {
      setQuestion(confirm());
      return;
    }

    setQuestion(null);
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
    // Mudar um campo durante a confirmação volta ao formulário: a pergunta valia para os antigos.
    <form className={styles.form} onSubmit={handleSubmit} onChange={() => setQuestion(null)} noValidate aria-label={title}>
      <h3>{title}</h3>

      {children}

      {error && <p className={styles.error} role="alert">{error}</p>}
      {info && <p className={styles.info} role="status">{info}</p>}
      {question && <p className={styles.info} role="status">{question}</p>}

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.secondary}
          onClick={question ? () => setQuestion(null) : onCancel}
          disabled={saving}
        >
          {question ? 'Voltar' : 'Cancelar'}
        </button>
        <button type="submit" className={styles.primary} disabled={saving}>
          {saving ? 'Salvando...' : question ? 'Confirmar' : submitLabel}
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

/**
 * Selo de situação das linhas do painel: "Ativo" ou "Desativado", ou `label` com a cor de
 * `active` (a situação da assinatura, SPEC/2026-11-26-painel-trim-club.md).
 */
export const StatusBadge = ({ active, label }: { active: boolean; label?: string }) => (
  <span className={`${styles.badge} ${active ? styles.badgeActive : styles.badgeInactive}`}>
    {label ?? (active ? 'Ativo' : 'Desativado')}
  </span>
);

export default AdminForm;
