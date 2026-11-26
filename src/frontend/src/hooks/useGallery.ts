import { useCallback } from 'react';
import api from '../api';
import { useApiResource } from './useApiResource';
import { upsert, useNameList, type NamedItem } from './useNameList';

// Galeria: fotos públicas com o filtro por tag, envio, moderação e tags
// (SPEC/2026-11-26-painel-galeria.md), sobre as rotas de /gallery
// (SPEC/2026-11-25-galeria-permissoes.md). As ações devolvem o que o backend gravou e lançam o
// erro da API, para quem chamou mostrar a mensagem.

export type GalleryTag = NamedItem;

export type Photo = {
  id: string;
  image_url: string;
  barber_id: string;
  service_id: string | null;
  description: string | null;
  is_approved: boolean;
  created_at: string;
  tags: GalleryTag[];
};

/** Envio de uma foto. O `barber_id` vai só quando o admin escolhe o barbeiro. */
export type PhotoInput = { image_url: string; description?: string; tag_ids: string[]; barber_id?: string };

/** Barbeiro ativo, como `GET /barbers` devolve (só o que a galeria usa). */
export type BarberOption = { id: string; full_name: string };

/** Mesma ordem do backend: a foto mais recente primeiro. */
const newestFirst = (a: Photo, b: Photo) => b.created_at.localeCompare(a.created_at);

const without = (id: string) => (list: Photo[]) => list.filter((photo) => photo.id !== id);

export const useGalleryTags = () => useNameList<GalleryTag>('/gallery/tags', 'Não foi possível carregar as tags.');

const loadBarbers = async () => (await api.get<BarberOption[]>('/barbers')).data;

/** Os barbeiros ativos, para a escolha no envio e o nome nas fotos. */
export function useBarberNames() {
  const { data: barbers, status } = useApiResource(loadBarbers, [] as BarberOption[], '');
  /** O nome do barbeiro; "Barbeiro inativo" quando ele não está entre os ativos; vazio antes da carga. */
  const nameOf = (id: string) =>
    status === 'ready' ? (barbers.find((b) => b.id === id)?.full_name ?? 'Barbeiro inativo') : '';
  return { barbers, nameOf };
}

/** Fotos aprovadas, só da tag `tagId` (vazio: todas). */
export function usePublicGallery(tagId: string) {
  const load = useCallback(
    async () => (await api.get<Photo[]>('/gallery', { params: tagId ? { tag_id: tagId } : {} })).data,
    [tagId],
  );
  return useApiResource(load, [] as Photo[], 'Não foi possível carregar a galeria.');
}

export async function sendPhoto(input: PhotoInput): Promise<Photo> {
  return (await api.post<Photo>('/gallery', input)).data;
}

const loadPending = async () => (await api.get<Photo[]>('/gallery/pending')).data;
const loadPublished = async () => (await api.get<Photo[]>('/gallery')).data;
const skip = async () => [] as Photo[];

/**
 * Fotos pendentes e publicadas, com as ações do admin. Com `enabled` falso (barbeiro), não chama
 * a API: as rotas de moderação são só do admin.
 */
export function useGalleryModeration(enabled: boolean) {
  const pending = useApiResource(enabled ? loadPending : skip, [] as Photo[], 'Não foi possível carregar as fotos pendentes.');
  const published = useApiResource(enabled ? loadPublished : skip, [] as Photo[], 'Não foi possível carregar as fotos publicadas.');
  const setPending = pending.setData;
  const setPublished = published.setData;

  /** Põe a foto na lista da situação dela (publicada ou pendente) e tira da outra. */
  const place = useCallback(
    (photo: Photo) => {
      const [target, other] = photo.is_approved ? [setPublished, setPending] : [setPending, setPublished];
      other(without(photo.id));
      target((current) => upsert(current, photo, newestFirst));
      return photo;
    },
    [setPending, setPublished],
  );

  const approve = useCallback(
    async (id: string) => place((await api.put<Photo>(`/gallery/${id}/approve`)).data),
    [place],
  );

  const unapprove = useCallback(
    async (id: string) => place((await api.put<Photo>(`/gallery/${id}/unapprove`)).data),
    [place],
  );

  const reject = useCallback(
    async (id: string, reason: string) => {
      await api.put(`/gallery/${id}/reject`, { reason });
      setPending(without(id));
    },
    [setPending],
  );

  const remove = useCallback(
    async (id: string) => {
      await api.delete(`/gallery/${id}`);
      setPending(without(id));
      setPublished(without(id));
    },
    [setPending, setPublished],
  );

  return { pending, published, place, approve, unapprove, reject, remove };
}
