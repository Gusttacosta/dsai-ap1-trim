import React, { useState } from 'react';
import type { AdminService, ServiceChanges, ServiceInput } from '../../hooks/useAdminServices';
import AdminForm, { FormField } from '../AdminForm';
import {
  parseDuration,
  parsePrice,
  priceToInput,
  validateDuration,
  validatePrice,
  validateServiceName,
} from '../../utils/serviceValidation';

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

  const set = (key: keyof ServiceFields) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => setFields((current) => ({ ...current, [key]: event.target.value }));

  const save = async () => {
    const data = service ? serviceChanges(service, fields) : serviceInput(fields);
    if (Object.keys(data).length === 0) return false;
    await onSave(data);
    return true;
  };

  return (
    <AdminForm
      title={service ? 'Editar serviço' : 'Novo serviço'}
      submitLabel="Salvar serviço"
      errorFallback="Não foi possível salvar o serviço."
      validate={() => validateServiceName(fields.name) ?? validatePrice(fields.price) ?? validateDuration(fields.duration)}
      save={save}
      onCancel={onCancel}
    >
      <FormField id="servico-nome" label="Nome" wide>
        <input id="servico-nome" value={fields.name} onChange={set('name')} />
      </FormField>

      <FormField id="servico-descricao" label="Descrição (opcional)" wide>
        <textarea id="servico-descricao" rows={2} value={fields.description} onChange={set('description')} />
      </FormField>

      <FormField id="servico-preco" label="Preço (R$)">
        <input id="servico-preco" inputMode="decimal" placeholder="35,00" value={fields.price} onChange={set('price')} />
      </FormField>

      <FormField id="servico-duracao" label="Duração (min)">
        <input id="servico-duracao" inputMode="numeric" placeholder="30" value={fields.duration} onChange={set('duration')} />
      </FormField>
    </AdminForm>
  );
};

export default ServiceForm;
