import React, { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import styles from '../services/Services.module.css';
import AdminForm, { FormField } from '../AdminForm';
import type { BarberOption, GalleryTag, PhotoInput } from '../../hooks/useGallery';
import { BARBER_ERROR, validateImageUrl, validatePhotoDescription } from '../../utils/galleryValidation';

// Envio de uma foto para a galeria (SPEC/2026-11-26-painel-galeria.md). O barbeiro envia para o
// próprio portfólio, sem `barber_id`; o admin escolhe o barbeiro (obrigatório).

type Props = {
  isAdmin: boolean;
  tags: GalleryTag[];
  /** Barbeiros ativos, para a escolha do admin. */
  barbers: BarberOption[];
  /** Envia. Quem chamou fecha o formulário depois. */
  onSend: (input: PhotoInput) => Promise<void>;
  onCancel: () => void;
};

/** O envio no formato da API: URL e descrição aparadas, descrição vazia fora. */
export function photoInput(url: string, description: string, tagIds: string[], barberId: string): PhotoInput {
  const input: PhotoInput = { image_url: url.trim(), tag_ids: tagIds };
  if (description.trim()) input.description = description.trim();
  if (barberId) input.barber_id = barberId;
  return input;
}

const PhotoUploadForm = ({ isAdmin, tags, barbers, onSend, onCancel }: Props) => {
  const [url, setUrl] = useState('');
  const [description, setDescription] = useState('');
  const [tagIds, setTagIds] = useState<string[]>([]);
  const [barberId, setBarberId] = useState('');

  const toggle = (id: string) =>
    setTagIds((current) => (current.includes(id) ? current.filter((t) => t !== id) : [...current, id]));

  const validate = () =>
    validateImageUrl(url) ?? validatePhotoDescription(description) ?? (isAdmin && !barberId ? BARBER_ERROR : null);

  const save = async () => {
    await onSend(photoInput(url, description, tagIds, isAdmin ? barberId : ''));
    return true;
  };

  return (
    <AdminForm
      title="Enviar foto"
      submitLabel="Enviar foto"
      errorFallback="Não foi possível enviar a foto."
      validate={validate}
      save={save}
      onCancel={onCancel}
    >
      <FormField id="foto-url" label="URL da imagem" wide>
        <input
          id="foto-url"
          type="url"
          placeholder="https://..."
          value={url}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUrl(e.target.value)}
        />
      </FormField>

      <FormField id="foto-descricao" label="Descrição (opcional)" wide>
        <textarea id="foto-descricao" value={description} onChange={(e) => setDescription(e.target.value)} />
      </FormField>

      {isAdmin && (
        <FormField id="foto-barbeiro" label="Barbeiro">
          <select id="foto-barbeiro" value={barberId} onChange={(e) => setBarberId(e.target.value)}>
            <option value="">Escolha o barbeiro</option>
            {barbers.map((b) => (
              <option key={b.id} value={b.id}>{b.full_name}</option>
            ))}
          </select>
        </FormField>
      )}

      <fieldset className={`${styles.wide} ${shared.checks}`}>
        <legend>Tags</legend>
        {tags.length === 0 && <p>Nenhuma tag cadastrada.</p>}
        {tags.map((t) => (
          <label key={t.id}>
            <input type="checkbox" checked={tagIds.includes(t.id)} onChange={() => toggle(t.id)} /> {t.name}
          </label>
        ))}
      </fieldset>
    </AdminForm>
  );
};

export default PhotoUploadForm;
