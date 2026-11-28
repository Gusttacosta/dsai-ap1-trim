import React, { useState } from 'react';
import type { Reward, RewardChanges, RewardInput } from '../../hooks/useLoyaltyAdmin';
import { parsePoints, validatePointsCost, validateRewardDescription, validateRewardName } from '../../utils/loyalty';
import AdminForm, { FormField } from '../AdminForm';

// Formulário de criação e de edição de um prêmio da fidelidade (SPEC/2026-11-26-painel-fidelidade.md).

export type RewardFields = { name: string; description: string; cost: string };

type Props = {
  /** Prêmio em edição. Sem ele, o formulário cria um prêmio novo. */
  reward?: Reward;
  /** Criação: recebe todos os campos. Edição: só os que mudaram. */
  onSave: (data: RewardInput | RewardChanges) => Promise<unknown>;
  onCancel: () => void;
};

/** Campos do formulário no formato da API. Só chamar depois de validar. */
export function rewardInput(fields: RewardFields): RewardInput {
  return {
    name: fields.name.trim(),
    description: fields.description.trim() || null,
    points_cost: parsePoints(fields.cost) as number,
  };
}

/** Campos alterados em relação ao prêmio salvo. */
export function rewardChanges(reward: Reward, fields: RewardFields): RewardChanges {
  const input = rewardInput(fields);
  return Object.fromEntries(
    (Object.keys(input) as (keyof RewardInput)[])
      .filter((key) => input[key] !== (reward[key] ?? null))
      .map((key) => [key, input[key]]),
  );
}

const RewardForm = ({ reward, onSave, onCancel }: Props) => {
  const [fields, setFields] = useState<RewardFields>(() => ({
    name: reward?.name ?? '',
    description: reward?.description ?? '',
    cost: reward ? String(reward.points_cost) : '',
  }));

  const set = (key: keyof RewardFields) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setFields((current) => ({ ...current, [key]: event.target.value }));

  const validate = () =>
    validateRewardName(fields.name) ?? validateRewardDescription(fields.description) ?? validatePointsCost(fields.cost);

  const save = async () => {
    const data = reward ? rewardChanges(reward, fields) : rewardInput(fields);
    if (Object.keys(data).length === 0) return false;
    await onSave(data);
    return true;
  };

  return (
    <AdminForm
      title={reward ? 'Editar prêmio' : 'Novo prêmio'}
      submitLabel="Salvar prêmio"
      errorFallback="Não foi possível salvar o prêmio."
      validate={validate}
      save={save}
      onCancel={onCancel}
    >
      <FormField id="premio-nome" label="Nome">
        <input id="premio-nome" value={fields.name} onChange={set('name')} />
      </FormField>

      <FormField id="premio-custo" label="Custo (pontos)">
        <input id="premio-custo" inputMode="numeric" placeholder="120" value={fields.cost} onChange={set('cost')} />
      </FormField>

      <FormField id="premio-descricao" label="Descrição (opcional)" wide>
        <textarea id="premio-descricao" rows={2} value={fields.description} onChange={set('description')} />
      </FormField>
    </AdminForm>
  );
};

export default RewardForm;
