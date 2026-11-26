import { useState } from 'react';
import type { AdjustAction, Wallet } from '../../hooks/useLoyaltyAdmin';
import { formatPoints, parsePoints, validateAdjustPoints, validateAdjustReason } from '../../utils/loyalty';
import AdminForm, { FormField } from '../AdminForm';

// Ajuste manual dos pontos de um cliente (SPEC/2026-11-26-painel-fidelidade.md): adicionar ou
// retirar, com o motivo obrigatório, que vai na notificação do cliente. Pede confirmação, com o
// saldo antes e depois, antes de chamar a API.

type Props = {
  wallet: Wallet;
  /** Grava o ajuste. O erro da API (saldo insuficiente) aparece no formulário. */
  onSave: (action: AdjustAction, points: number, reason: string) => Promise<unknown>;
  onCancel: () => void;
};

const VERBS: Record<AdjustAction, string> = { add: 'Adicionar', remove: 'Retirar' };

/** "Adicionar 50 pts a Ana Lima? O saldo passa de 120 para 170 pts. Motivo: Aniversário." */
export function adjustQuestion(wallet: Wallet, action: AdjustAction, points: number, reason: string): string {
  const after = action === 'add' ? wallet.balance + points : wallet.balance - points;
  const target = action === 'add' ? 'a' : 'de';
  return (
    `${VERBS[action]} ${formatPoints(points)} ${target} ${wallet.full_name}? ` +
    `O saldo passa de ${wallet.balance.toLocaleString('pt-BR')} para ${formatPoints(after)}. Motivo: ${reason.trim()}.`
  );
}

const AdjustPointsForm = ({ wallet, onSave, onCancel }: Props) => {
  const [action, setAction] = useState<AdjustAction>('add');
  const [points, setPoints] = useState('');
  const [reason, setReason] = useState('');

  const validate = () => validateAdjustPoints(points) ?? validateAdjustReason(reason);
  const amount = () => parsePoints(points) as number;

  const save = async () => {
    await onSave(action, amount(), reason.trim());
    return true;
  };

  return (
    <AdminForm
      title={`Ajustar pontos de ${wallet.full_name}`}
      submitLabel="Ajustar pontos"
      errorFallback="Não foi possível ajustar os pontos."
      validate={validate}
      confirm={() => adjustQuestion(wallet, action, amount(), reason)}
      save={save}
      onCancel={onCancel}
    >
      <FormField id="ajuste-operacao" label="Operação">
        <select id="ajuste-operacao" value={action} onChange={(e) => setAction(e.target.value as AdjustAction)}>
          <option value="add">Adicionar</option>
          <option value="remove">Retirar</option>
        </select>
      </FormField>

      <FormField id="ajuste-pontos" label="Pontos">
        <input id="ajuste-pontos" inputMode="numeric" placeholder="50" value={points} onChange={(e) => setPoints(e.target.value)} />
      </FormField>

      <FormField id="ajuste-motivo" label="Motivo (o cliente vê na notificação)" wide>
        <input id="ajuste-motivo" value={reason} onChange={(e) => setReason(e.target.value)} />
      </FormField>
    </AdminForm>
  );
};

export default AdjustPointsForm;
