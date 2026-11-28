import React, { useState } from 'react';
import type { PlanChanges, PlanInput, SubscriptionPlan } from '../../hooks/useTrimClub';
import { priceToInput } from '../../utils/serviceValidation';
import {
  parseDiscount,
  parseMonthlyPrice,
  parseQuantity,
  validateDiscount,
  validateMonthlyPrice,
  validatePlanName,
  validateQuantity,
} from '../../utils/trimClub';
import AdminForm, { FormField } from '../AdminForm';
import styles from '../services/Services.module.css';

// Formulário de criação e de edição de um plano do Trim Club (SPEC/2026-11-26-painel-trim-club.md).
// Cortes e barbas inclusos têm a caixa "Ilimitados", que manda null (#16).

/** Quantidade inclusa como está na tela: o número digitado e a caixa "Ilimitados". */
type Quantity = { text: string; unlimited: boolean };

export type PlanFields = {
  name: string;
  description: string;
  price: string;
  cuts: Quantity;
  shaves: Quantity;
  discount: string;
};

type Props = {
  /** Plano em edição. Sem ele, o formulário cria um plano novo. */
  plan?: SubscriptionPlan;
  /** Criação: recebe todos os campos. Edição: só os que mudaram. */
  onSave: (data: PlanInput | PlanChanges) => Promise<unknown>;
  onCancel: () => void;
};

const CUTS_LABEL = 'Cortes inclusos';
const SHAVES_LABEL = 'Barbas inclusas';

const quantityValue = ({ text, unlimited }: Quantity) => (unlimited ? null : (parseQuantity(text) as number));

/** Campos do formulário no formato da API. Só chamar depois de validar. */
export function planInput(fields: PlanFields): PlanInput {
  return {
    name: fields.name.trim(),
    description: fields.description.trim() || null,
    monthly_price: parseMonthlyPrice(fields.price) as string,
    included_cuts: quantityValue(fields.cuts),
    included_shaves: quantityValue(fields.shaves),
    discount_percentage: parseDiscount(fields.discount) as string,
  };
}

/** Campos alterados em relação ao plano salvo. Preço e desconto são comparados pelo valor. */
export function planChanges(plan: SubscriptionPlan, fields: PlanFields): PlanChanges {
  const input = planInput(fields);
  const changes: PlanChanges = {};
  if (input.name !== plan.name) changes.name = input.name;
  if (input.description !== (plan.description || null)) changes.description = input.description;
  if (Number(input.monthly_price) !== Number(plan.monthly_price)) changes.monthly_price = input.monthly_price;
  if (input.included_cuts !== plan.included_cuts) changes.included_cuts = input.included_cuts;
  if (input.included_shaves !== plan.included_shaves) changes.included_shaves = input.included_shaves;
  if (Number(input.discount_percentage) !== Number(plan.discount_percentage)) {
    changes.discount_percentage = input.discount_percentage;
  }
  return changes;
}

const toQuantity = (value: number | null): Quantity =>
  value === null ? { text: '', unlimited: true } : { text: String(value), unlimited: false };

function initialFields(plan?: SubscriptionPlan): PlanFields {
  if (!plan) {
    return { name: '', description: '', price: '', cuts: toQuantity(0), shaves: toQuantity(0), discount: '' };
  }
  return {
    name: plan.name,
    description: plan.description ?? '',
    price: priceToInput(plan.monthly_price),
    cuts: toQuantity(plan.included_cuts),
    shaves: toQuantity(plan.included_shaves),
    discount: Number(plan.discount_percentage) > 0 ? priceToInput(plan.discount_percentage) : '',
  };
}

/** Quantidade inclusa: o número, desligado quando "Ilimitados" está marcada. */
const QuantityField = ({ id, label, value, onChange }: {
  id: string;
  label: string;
  value: Quantity;
  onChange: (value: Quantity) => void;
}) => (
  <>
    <FormField id={id} label={label}>
      <input
        id={id}
        inputMode="numeric"
        value={value.text}
        disabled={value.unlimited}
        onChange={(e) => onChange({ ...value, text: e.target.value })}
      />
    </FormField>
    <label className={styles.check}>
      <input
        type="checkbox"
        aria-label={`${label}: ilimitados`}
        checked={value.unlimited}
        onChange={(e) => onChange({ ...value, unlimited: e.target.checked })}
      />{' '}
      Ilimitados
    </label>
  </>
);

const PlanForm = ({ plan, onSave, onCancel }: Props) => {
  const [fields, setFields] = useState<PlanFields>(() => initialFields(plan));

  const update = <K extends keyof PlanFields>(key: K, value: PlanFields[K]) =>
    setFields((current) => ({ ...current, [key]: value }));
  const set = (key: 'name' | 'description' | 'price' | 'discount') => (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => update(key, event.target.value);

  const validate = () =>
    validatePlanName(fields.name) ??
    validateMonthlyPrice(fields.price) ??
    validateQuantity(fields.cuts.text, fields.cuts.unlimited, CUTS_LABEL) ??
    validateQuantity(fields.shaves.text, fields.shaves.unlimited, SHAVES_LABEL) ??
    validateDiscount(fields.discount);

  const save = async () => {
    const data = plan ? planChanges(plan, fields) : planInput(fields);
    if (Object.keys(data).length === 0) return false;
    await onSave(data);
    return true;
  };

  return (
    <AdminForm
      title={plan ? 'Editar plano' : 'Novo plano'}
      submitLabel="Salvar plano"
      errorFallback="Não foi possível salvar o plano."
      validate={validate}
      save={save}
      onCancel={onCancel}
    >
      <FormField id="plano-nome" label="Nome" wide>
        <input id="plano-nome" value={fields.name} onChange={set('name')} />
      </FormField>

      <FormField id="plano-descricao" label="Descrição (opcional)" wide>
        <textarea id="plano-descricao" rows={2} value={fields.description} onChange={set('description')} />
      </FormField>

      <FormField id="plano-preco" label="Preço mensal (R$)">
        <input id="plano-preco" inputMode="decimal" placeholder="49,90" value={fields.price} onChange={set('price')} />
      </FormField>

      <FormField id="plano-desconto" label="Desconto (%)">
        <input id="plano-desconto" inputMode="decimal" placeholder="0" value={fields.discount} onChange={set('discount')} />
      </FormField>

      <QuantityField id="plano-cortes" label={CUTS_LABEL} value={fields.cuts} onChange={(v) => update('cuts', v)} />
      <QuantityField id="plano-barbas" label={SHAVES_LABEL} value={fields.shaves} onChange={(v) => update('shaves', v)} />
    </AdminForm>
  );
};

export default PlanForm;
