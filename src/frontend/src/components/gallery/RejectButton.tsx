import { useState, type ReactNode } from 'react';
import shared from '../../pages/AdminShared.module.css';
import { validateReason } from '../../utils/galleryValidation';

// "Recusar" de uma foto pendente (SPEC/2026-11-26-painel-galeria.md): abre, na linha, o campo do
// motivo com "Confirmar recusa" e "Voltar". O motivo é conferido antes da API e vai aparado.

type Props = {
  busy: boolean;
  /** Recusa com o motivo. Devolve true quando deu certo, para o campo fechar. */
  onReject: (reason: string) => Promise<boolean>;
  /** Outras ações, escondidas enquanto o motivo é pedido. */
  children?: ReactNode;
};

const RejectButton = ({ busy, onReject, children }: Props) => {
  // null: fechado.
  const [reason, setReason] = useState<string | null>(null);
  const [invalid, setInvalid] = useState('');

  const confirm = async () => {
    const problem = validateReason(reason ?? '');
    setInvalid(problem ?? '');
    if (!problem && (await onReject((reason ?? '').trim()))) setReason(null);
  };

  if (reason === null) {
    return (
      <>
        {children}
        <button type="button" className={`${shared.btnIcon} ${shared.btnDanger}`} onClick={() => setReason('')} disabled={busy}>
          Recusar
        </button>
      </>
    );
  }

  return (
    <>
      <input aria-label="Motivo da recusa" placeholder="Motivo da recusa" value={reason} onChange={(e) => setReason(e.target.value)} />
      <button type="button" className={`${shared.btnIcon} ${shared.btnDanger}`} onClick={confirm} disabled={busy}>
        Confirmar recusa
      </button>
      <button
        type="button"
        className={shared.btnIcon}
        onClick={() => {
          setReason(null);
          setInvalid('');
        }}
        disabled={busy}
      >
        Voltar
      </button>
      {invalid && <span className={shared.confirmQuestion} role="alert">{invalid}</span>}
    </>
  );
};

export default RejectButton;
