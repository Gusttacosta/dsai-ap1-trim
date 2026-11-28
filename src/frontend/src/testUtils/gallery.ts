import type { BarberOption, GalleryTag, Photo } from '../hooks/useGallery';

// Fotos, tags e barbeiros como a API os devolve, para os testes da galeria
// (SPEC/2026-11-26-painel-galeria.md).

export const tag = (name: string): GalleryTag => ({ id: name.toLowerCase(), name });

export const FADE = tag('Fade');
export const BARBA = tag('Barba');

export const JOAO: BarberOption = { id: 'b1', full_name: 'João Silva' };
export const CARLOS: BarberOption = { id: 'b2', full_name: 'Carlos Santos' };

export function makePhoto(id: string, extra: Partial<Photo> = {}): Photo {
  return {
    id,
    image_url: `https://fotos.exemplo.com/${id}.jpg`,
    barber_id: JOAO.id,
    service_id: null,
    description: `Corte ${id}`,
    is_approved: false,
    created_at: '2026-11-20T15:00:00Z',
    tags: [],
    ...extra,
  };
}
