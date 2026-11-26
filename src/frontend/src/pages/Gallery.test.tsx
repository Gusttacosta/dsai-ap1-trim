// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import type { Photo } from '../hooks/useGallery';
import { BARBA, CARLOS, FADE, JOAO, makePhoto } from '../testUtils/gallery';
import { httpError } from '../testUtils/httpError';
import Gallery from './Gallery';

// SPEC/2026-11-26-painel-galeria.md: a galeria pública com as fotos da API e o filtro por tag.

vi.mock('../api', () => ({ default: { get: vi.fn() } }));
const mockedGet = api.get as unknown as ReturnType<typeof vi.fn>;

const FADE_PHOTO = makePhoto('p1', { description: 'Degradê', is_approved: true, tags: [FADE] });
const BEARD_PHOTO = makePhoto('p2', { description: 'Barba feita', barber_id: CARLOS.id, is_approved: true, tags: [BARBA] });

/** A API simulada: as fotos de cada filtro (a chave é o tag_id, vazio para todas). */
function serve(byTag: Record<string, Photo[] | Error>) {
  mockedGet.mockImplementation((url: string, config?: { params?: { tag_id?: string } }) => {
    if (url === '/gallery/tags') return Promise.resolve({ data: [BARBA, FADE] });
    if (url === '/barbers') return Promise.resolve({ data: [JOAO, CARLOS] });
    const photos = byTag[config?.params?.tag_id ?? ''];
    return photos instanceof Error ? Promise.reject(photos) : Promise.resolve({ data: photos ?? [] });
  });
}

const cards = () => screen.queryAllByRole('figure').map((card) => card.getAttribute('aria-label'));
const filterButton = (name: string) => within(screen.getByRole('group', { name: 'Filtrar por tag' })).getByRole('button', { name });
const galleryCalls = () => mockedGet.mock.calls.filter(([url]) => url === '/gallery');

beforeEach(() => mockedGet.mockReset());
afterEach(cleanup);

describe('Gallery', () => {
  it('mostra as fotos da API com o nome do barbeiro e as tags, sem as fotos fixas', async () => {
    serve({ '': [FADE_PHOTO, BEARD_PHOTO] });
    render(<Gallery />);

    await waitFor(() => expect(cards()).toEqual(['Degradê', 'Barba feita']));
    expect(galleryCalls()[0]).toEqual(['/gallery', { params: {} }]);
    const beard = screen.getByRole('figure', { name: 'Barba feita' });
    expect(await within(beard).findByText('Carlos Santos')).toBeTruthy();
    expect(within(beard).getByText('Barba')).toBeTruthy();
    expect((within(beard).getByRole('img') as HTMLImageElement).src).toBe(BEARD_PHOTO.image_url);
    expect(screen.queryByText('Marcos Almeida')).toBeNull();
  });

  it('os filtros são "Todas" e as tags da API', async () => {
    serve({ '': [] });
    render(<Gallery />);

    await screen.findByRole('button', { name: 'Fade' });
    const names = within(screen.getByRole('group', { name: 'Filtrar por tag' }))
      .getAllByRole('button')
      .map((b) => b.textContent);
    expect(names).toEqual(['Todas', 'Barba', 'Fade']);
    expect(filterButton('Todas').getAttribute('aria-pressed')).toBe('true');
  });

  it('a tag escolhida vai como tag_id, e "Todas" tira o filtro', async () => {
    serve({ '': [FADE_PHOTO, BEARD_PHOTO], fade: [FADE_PHOTO] });
    render(<Gallery />);
    await waitFor(() => expect(cards()).toHaveLength(2));

    fireEvent.click(await screen.findByRole('button', { name: 'Fade' }));

    await waitFor(() => expect(cards()).toEqual(['Degradê']));
    expect(galleryCalls().at(-1)).toEqual(['/gallery', { params: { tag_id: 'fade' } }]);
    expect(filterButton('Fade').getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(filterButton('Todas'));

    await waitFor(() => expect(cards()).toHaveLength(2));
    expect(galleryCalls().at(-1)).toEqual(['/gallery', { params: {} }]);
  });

  it('sem fotos, avisa', async () => {
    serve({ '': [] });
    render(<Gallery />);

    expect(await screen.findByText('Nenhuma foto por aqui ainda.')).toBeTruthy();
  });

  it('a falha mostra a mensagem e "Tentar de novo" carrega outra vez', async () => {
    serve({ '': httpError(500) });
    render(<Gallery />);

    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível carregar a galeria.');
    serve({ '': [FADE_PHOTO] });
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));

    await waitFor(() => expect(cards()).toEqual(['Degradê']));
  });
});
