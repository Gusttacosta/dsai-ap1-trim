import React, { useState } from 'react';
import type { Expense, ExpenseCategory, ExpenseChanges, ExpenseInput } from '../../hooks/useAdminExpenses';
import { parseAmount, validateAmount, validateDescription, validatePaymentDate } from '../../utils/expenseValidation';
import { priceToInput } from '../../utils/serviceValidation';
import AdminForm, { FormField } from '../AdminForm';
import styles from '../services/Services.module.css';

// Formulário de criação e de edição de uma despesa (SPEC/2026-11-26-painel-despesas.md).

export type ExpenseFields = {
  description: string;
  amount: string;
  date: string;
  /** "" é "Sem categoria". */
  categoryId: string;
  recurring: boolean;
};

type Props = {
  /** Despesa em edição. Sem ela, o formulário lança uma despesa nova. */
  expense?: Expense;
  categories: ExpenseCategory[];
  /** Criação: recebe todos os campos. Edição: só os que mudaram. */
  onSave: (data: ExpenseInput | ExpenseChanges) => Promise<unknown>;
  onCancel: () => void;
};

/** Campos do formulário no formato da API. Só chamar depois de validar. */
export function expenseInput(fields: ExpenseFields): ExpenseInput {
  return {
    category_id: fields.categoryId || null,
    description: fields.description.trim(),
    amount: parseAmount(fields.amount) as string,
    payment_date: fields.date,
    is_recurring: fields.recurring,
  };
}

/** Campos alterados em relação à despesa salva. O valor é comparado pelo número. */
export function expenseChanges(expense: Expense, fields: ExpenseFields): ExpenseChanges {
  const input = expenseInput(fields);
  const changes: ExpenseChanges = {};
  if (input.category_id !== expense.category_id) changes.category_id = input.category_id;
  if (input.description !== expense.description) changes.description = input.description;
  if (Number(input.amount) !== Number(expense.amount)) changes.amount = input.amount;
  if (input.payment_date !== expense.payment_date) changes.payment_date = input.payment_date;
  if (input.is_recurring !== expense.is_recurring) changes.is_recurring = input.is_recurring;
  return changes;
}

function initialFields(expense?: Expense): ExpenseFields {
  if (!expense) return { description: '', amount: '', date: '', categoryId: '', recurring: false };
  return {
    description: expense.description,
    amount: priceToInput(expense.amount),
    date: expense.payment_date,
    categoryId: expense.category_id ?? '',
    recurring: expense.is_recurring,
  };
}

const ExpenseForm = ({ expense, categories, onSave, onCancel }: Props) => {
  const [fields, setFields] = useState<ExpenseFields>(() => initialFields(expense));

  const set = (key: Exclude<keyof ExpenseFields, 'recurring'>) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => setFields((current) => ({ ...current, [key]: event.target.value }));

  const save = async () => {
    const data = expense ? expenseChanges(expense, fields) : expenseInput(fields);
    if (Object.keys(data).length === 0) return false;
    await onSave(data);
    return true;
  };

  return (
    <AdminForm
      title={expense ? 'Editar despesa' : 'Nova despesa'}
      submitLabel="Salvar despesa"
      errorFallback="Não foi possível salvar a despesa."
      validate={() =>
        validateDescription(fields.description) ?? validateAmount(fields.amount) ?? validatePaymentDate(fields.date)
      }
      save={save}
      onCancel={onCancel}
    >
      <FormField id="despesa-descricao" label="Descrição" wide>
        <input id="despesa-descricao" value={fields.description} onChange={set('description')} />
      </FormField>

      <FormField id="despesa-valor" label="Valor (R$)">
        <input id="despesa-valor" inputMode="decimal" placeholder="100,00" value={fields.amount} onChange={set('amount')} />
      </FormField>

      <FormField id="despesa-data" label="Data do pagamento">
        <input id="despesa-data" type="date" value={fields.date} onChange={set('date')} />
      </FormField>

      <FormField id="despesa-categoria" label="Categoria">
        <select id="despesa-categoria" value={fields.categoryId} onChange={set('categoryId')}>
          <option value="">Sem categoria</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </FormField>

      <label className={styles.check}>
        <input
          type="checkbox"
          checked={fields.recurring}
          onChange={(e) => setFields((current) => ({ ...current, recurring: e.target.checked }))}
        />{' '}
        Despesa recorrente
      </label>
    </AdminForm>
  );
};

export default ExpenseForm;
