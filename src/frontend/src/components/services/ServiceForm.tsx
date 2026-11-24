import React, { useState } from 'react';
import type { AdminService, ServiceChanges, ServiceInput } from '../../hooks/useAdminServices';
import { apiErrorMessage } from '../../utils/apiError';
import {
  parseDuration,
  parsePrice,
  priceToInput,
  validateDuration,
  validatePrice,
  validateServiceName,
} from '../../utils/serviceValidation';
import styles from './Services.module.css';

// Formulário de criação e de edição de um serviço (SPEC/2026-11-23-painel-servicos.md).

export type ServiceFields = { name: string; description: string; price: string; duration: string };

type Props = {
  /** Serviço em edição. Sem ele, o formulário cria um serviço novo. */
  service?: AdminService;
  /** Criação: recebe todos os campos. Edição: só os que mudaram. */
  onSave: (data: ServiceInput | ServiceChanges) => Promise<unknown>;
  onCancel: () => void;
};

/** Campos do formulário no formato da API. Só chamar depois de validar. */
export function serviceInput(fields: ServiceFields): ServiceInput {
  return {
    name: fields.name.trim(),
    description: fields.description.trim() || null,
    price: parsePrice(fields.price) as string,
    duration_minutes: parseDuration(fields.duration) as number,
  };
}

/** Campos alterados em relação ao serviço salvo. O preço é comparado pelo valor. */
export function serviceChanges(service: AdminService, fields: ServiceFields): ServiceChanges {
  const input = serviceInput(fields);
  const changes: ServiceChanges = {};
  if (input.name !== service.name) changes.name = input.name;
  if (input.description !== (service.description || null)) changes.description = input.description;
  if (Number(input.price) !== Number(service.price)) changes.price = input.price;
  if (input.duration_minutes !== service.duration_minutes) changes.duration_minutes = input.duration_minutes;
  return changes;
}

function initialFields(service?: AdminService): ServiceFields {
  if (!service) return { name: '', description: '', price: '', duration: '' };
  return {
    name: service.name,
    description: service.description ?? '',
    price: priceToInput(service.price),
    duration: String(service.duration_minutes),
  };
}

const ServiceForm = ({ service, onSave, onCancel }: Props) => {
  const [fields, setFields] = useState<ServiceFields>(() => initialFields(service));
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [saving, setSaving] = useState(false);

  const editing = service !== undefined;
  const title = editing ? 'Editar serviço' : 'Novo serviço';
  const set = (key: keyof ServiceFields) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => setFields((current) => ({ ...current, [key]: event.target.value }));

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setInfo('');

    const problem =
      validateServiceName(fields.name) ?? validatePrice(fields.price) ?? validateDuration(fields.duration);
    if (problem) {
      setError(problem);
      return;
    }

    const data = editing ? serviceChanges(service, fields) : serviceInput(fields);
    if (Object.keys(data).length === 0) {
      setInfo('Nada mudou.');
      return;
    }

    setSaving(true);
    try {
      // Quem chamou fecha o formulário depois de salvar: daqui em diante ele some.
      await onSave(data);
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível salvar o serviço.'));
      setSaving(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate aria-label={title}>
      <h3>{title}</h3>

      <div className={`${styles.field} ${styles.wide}`}>
        <label htmlFor="servico-nome">Nome</label>
        <input id="servico-nome" value={fields.name} onChange={set('name')} />
      </div>

      <div className={`${styles.field} ${styles.wide}`}>
        <label htmlFor="servico-descricao">Descrição (opcional)</label>
        <textarea id="servico-descricao" rows={2} value={fields.description} onChange={set('description')} />
      </div>

      <div className={styles.field}>
        <label htmlFor="servico-preco">Preço (R$)</label>
        <input id="servico-preco" inputMode="decimal" placeholder="35,00" value={fields.price} onChange={set('price')} />
      </div>

      <div className={styles.field}>
        <label htmlFor="servico-duracao">Duração (min)</label>
        <input id="servico-duracao" inputMode="numeric" placeholder="30" value={fields.duration} onChange={set('duration')} />
      </div>

      {error && <p className={styles.error} role="alert">{error}</p>}
      {info && <p className={styles.info} role="status">{info}</p>}

      <div className={styles.actions}>
        <button type="button" className={styles.secondary} onClick={onCancel} disabled={saving}>
          Cancelar
        </button>
        <button type="submit" className={styles.primary} disabled={saving}>
          {saving ? 'Salvando...' : 'Salvar serviço'}
        </button>
      </div>
    </form>
  );
};

export default ServiceForm;
