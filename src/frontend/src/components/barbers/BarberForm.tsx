import React, { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import AdminForm, { FormField } from '../AdminForm';
import LoadState from '../LoadState';
import {
  useBarberServiceChoices,
  type AdminBarber,
  type BarberChanges,
  type BarberInput,
} from '../../hooks/useAdminBarbers';
import {
  parseCommission,
  validateBio,
  validateCommission,
  validateInstagram,
} from '../../utils/barberValidation';
import { priceToInput } from '../../utils/serviceValidation';
import styles from '../services/Services.module.css';

// Formulário de criação e de edição de um barbeiro: comissão, Instagram, bio e os serviços que
// ele faz (SPEC/2026-11-26-painel-barbeiros.md). A criação parte de um usuário já escolhido.

type Fields = { commission: string; instagram: string; bio: string };

/** O que salvar: o perfil (criação completa, ou só as mudanças) e os serviços, null se não mudaram. */
export type BarberSave =
  | { kind: 'create'; input: BarberInput; serviceIds: string[] | null }
  | { kind: 'update'; changes: BarberChanges; serviceIds: string[] | null };

type Props = {
  /** Barbeiro em edição. */
  barber?: AdminBarber;
  /** Na criação: o usuário escolhido, e "Trocar" para voltar à busca. */
  user?: { id: string; full_name: string; email: string };
  onChangeUser?: () => void;
  onSave: (data: BarberSave) => Promise<unknown>;
  onCancel: () => void;
};

function initialFields(barber?: AdminBarber): Fields {
  if (!barber) return { commission: '50', instagram: '', bio: '' };
  return {
    commission: priceToInput(barber.commission_rate),
    instagram: barber.instagram_url ?? '',
    bio: barber.bio ?? '',
  };
}

/** Campos alterados em relação ao barbeiro salvo. Texto apagado vira null. */
export function barberChanges(barber: AdminBarber, fields: Fields): BarberChanges {
  const changes: BarberChanges = {};
  const commission = parseCommission(fields.commission) as string;
  const bio = fields.bio.trim() || null;
  const instagram = fields.instagram.trim() || null;
  if (Number(commission) !== Number(barber.commission_rate)) changes.commission_rate = commission;
  if (bio !== (barber.bio || null)) changes.bio = bio;
  if (instagram !== (barber.instagram_url || null)) changes.instagram_url = instagram;
  return changes;
}

const sameSet = (a: string[], b: string[]) => a.length === b.length && a.every((id) => b.includes(id));

const BarberForm = ({ barber, user, onChangeUser, onSave, onCancel }: Props) => {
  const [fields, setFields] = useState<Fields>(() => initialFields(barber));
  const choices = useBarberServiceChoices(barber?.id ?? null);
  // null até o admin marcar ou desmarcar: vale o que está vinculado.
  const [picked, setPicked] = useState<string[] | null>(null);
  const selected = picked ?? choices.data.linkedIds;

  const set = (key: keyof Fields) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setFields((current) => ({ ...current, [key]: event.target.value }));

  const toggle = (id: string) =>
    setPicked(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);

  const save = async () => {
    const serviceIds = picked && !sameSet(picked, choices.data.linkedIds) ? picked : null;
    let data: BarberSave;
    if (barber) {
      const changes = barberChanges(barber, fields);
      if (Object.keys(changes).length === 0 && serviceIds === null) return false;
      data = { kind: 'update', changes, serviceIds };
    } else {
      const input: BarberInput = { user_id: user!.id, commission_rate: parseCommission(fields.commission) as string };
      if (fields.bio.trim()) input.bio = fields.bio.trim();
      if (fields.instagram.trim()) input.instagram_url = fields.instagram.trim();
      data = { kind: 'create', input, serviceIds };
    }
    await onSave(data);
    return true;
  };

  const who = barber ?? user;

  return (
    <AdminForm
      title={barber ? `Editar ${barber.full_name}` : 'Novo barbeiro'}
      submitLabel="Salvar barbeiro"
      errorFallback="Não foi possível salvar o barbeiro."
      validate={() =>
        validateCommission(fields.commission) ?? validateInstagram(fields.instagram) ?? validateBio(fields.bio)
      }
      save={save}
      onCancel={onCancel}
    >
      {who && (
        <p className={styles.wide}>
          {who.full_name} <span className={styles.description}>{who.email}</span>
          {onChangeUser && (
            <button type="button" className={shared.btnIcon} onClick={onChangeUser}>
              Trocar
            </button>
          )}
        </p>
      )}

      <FormField id="barbeiro-comissao" label="Comissão (%)">
        <input id="barbeiro-comissao" inputMode="decimal" value={fields.commission} onChange={set('commission')} />
      </FormField>

      <FormField id="barbeiro-instagram" label="Instagram (opcional)">
        <input
          id="barbeiro-instagram"
          type="url"
          placeholder="https://instagram.com/..."
          value={fields.instagram}
          onChange={set('instagram')}
        />
      </FormField>

      <FormField id="barbeiro-bio" label="Bio (opcional)" wide>
        <textarea id="barbeiro-bio" rows={3} value={fields.bio} onChange={set('bio')} />
      </FormField>

      <fieldset className={`${styles.wide} ${shared.checks}`}>
        <legend>Serviços que faz</legend>
        <LoadState
          status={choices.status}
          loadError={choices.loadError}
          reload={choices.reload}
          loadingText="Carregando serviços..."
        >
          {choices.data.options.length === 0 && <p>Nenhum serviço ativo.</p>}
          {choices.data.options.map((service) => (
            <label key={service.id}>
              <input type="checkbox" checked={selected.includes(service.id)} onChange={() => toggle(service.id)} />{' '}
              {service.name}
            </label>
          ))}
        </LoadState>
      </fieldset>
    </AdminForm>
  );
};

export default BarberForm;
