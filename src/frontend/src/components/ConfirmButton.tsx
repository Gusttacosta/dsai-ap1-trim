import { useState, type ReactNode } from 'react';
import shared from '../pages/AdminShared.module.css';

// Ação destrutiva com confirmação no próprio lugar: o botão vira a pergunta, "Confirmar" e
// "Voltar". Usado em "Desativar" serviço (SPEC/2026-11-23-painel-servicos.md) e em "Cancelar"
// agendamento (SPEC/2026-11-25-meus-agendamentos.md).

type Props = {
  /** Texto do botão que abre a confirmação. */
  label: string;
  /** Nome acessível do botão, quando o texto sozinho não basta (vários na mesma tela). */
  ariaLabel?: string;
  /** Pergunta mostrada no lugar do botão. */
  question: string;
  onConfirm: () => void;
  /** Uma ação está em andamento: os botões ficam desabilitados. */
  busy?: boolean;
  /** Outras ações, mostradas ao lado do botão e escondidas durante a confirmação. */
  children?: ReactNode;
};

const ConfirmButton = ({ label, ariaLabel, question, onConfirm, busy = false, children }: Props) => {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <>
        <span className={shared.confirmQuestion}>{question}</span>
        <button
          type="button"
          className={`${shared.btnIcon} ${shared.btnDanger}`}
          onClick={() => {
            setConfirming(false);
            onConfirm();
          }}
          disabled={busy}
        >
          Confirmar
        </button>
        <button type="button" className={shared.btnIcon} onClick={() => setConfirming(false)} disabled={busy}>
          Voltar
        </button>
      </>
    );
  }

  return (
    <>
      {children}
      <button
        type="button"
        className={`${shared.btnIcon} ${shared.btnDanger}`}
        aria-label={ariaLabel}
        onClick={() => setConfirming(true)}
        disabled={busy}
      >
        {label}
      </button>
    </>
  );
};

export default ConfirmButton;
