// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { BARBA, CARLOS, FADE, JOAO, makePhoto } from '../testUtils/gallery';
import { httpError } from '../testUtils/httpError';
import { sendPhoto, useBarberNames, useGalleryModeration, useGalleryTags, usePublicGallery } from './useGallery';

// SPEC/2026-11-26-painel-galeria.md: carga e ações da galeria, com a API simulada.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

const OLD = makePhoto('p1', { created_at: '2026-11-10T10:00:00Z' });
const NEW = makePhoto('p2', { created_at: '2026-11-22T10:00:00Z' });
const LIVE = makePhoto('p3', { is_approved: true, created_at: '2026-11-15T10:00:00Z' });

const ids = (list: { id: string }[]) => list.map((item) => item.id);

/** A API simulada da moderação: pendentes e publicadas. */
function serve(pending = [NEW, OLD], published = [LIVE]) {
  mocked.get.mockImplementation((url: string) =>
    Promise.resolve({ data: url === '/gallery/pending' ? pending : published }),
  );
}

async function moderation(pending = [NEW, OLD], published = [LIVE]) {
  serve(pending, published);
  const hook = renderHook(() => useGalleryModeration(true));
  await waitFor(() => expect(hook.result.current.published.status).toBe('ready'));
  await waitFor(() => expect(hook.result.current.pending.status).toBe('ready'));
  return hook;
}

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

describe('usePublicGallery', () => {
  it('sem tag, não manda filtro', async () => {
    mocked.get.mockResolvedValue({ data: [LIVE] });
    const { result } = renderHook(() => usePublicGallery(''));

    await waitFor(() => expect(result.current.status).toBe('ready'));
    expect(mocked.get).toHaveBeenCalledWith('/gallery', { params: {} });
    expect(result.current.data).toEqual([LIVE]);
  });

  it('a tag vai como tag_id, e trocar a tag carrega de novo', async () => {
    mocked.get.mockResolvedValue({ data: [] });
    const { rerender } = renderHook((tagId: string) => usePublicGallery(tagId), { initialProps: 'fade' });
    await waitFor(() => expect(mocked.get).toHaveBeenCalledWith('/gallery', { params: { tag_id: 'fade' } }));

    rerender('');

    await waitFor(() => expect(mocked.get).toHaveBeenLastCalledWith('/gallery', { params: {} }));
  });

  it('falha sem mensagem usa o texto padrão', async () => {
    mocked.get.mockRejectedValue(httpError(500));
    const { result } = renderHook(() => usePublicGallery(''));

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toBe('Não foi possível carregar a galeria.');
  });
});

describe('useBarberNames', () => {
  it('dá o nome dos ativos e "Barbeiro inativo" para quem não está na lista', async () => {
    mocked.get.mockResolvedValue({ data: [JOAO, CARLOS] });
    const { result } = renderHook(() => useBarberNames());
    expect(result.current.nameOf(JOAO.id)).toBe('');

    await waitFor(() => expect(result.current.barbers).toEqual([JOAO, CARLOS]));
    expect(mocked.get).toHaveBeenCalledWith('/barbers');
    expect(result.current.nameOf(CARLOS.id)).toBe('Carlos Santos');
    expect(result.current.nameOf('b9')).toBe('Barbeiro inativo');
  });
});

describe('useGalleryTags', () => {
  it('carrega e cria pelas rotas de /gallery/tags', async () => {
    mocked.get.mockResolvedValue({ data: [BARBA, FADE] });
    const { result } = renderHook(() => useGalleryTags());
    await waitFor(() => expect(result.current.status).toBe('ready'));
    mocked.post.mockResolvedValue({ data: { id: 'afro', name: 'Afro' } });

    await act(() => result.current.create('Afro'));

    expect(mocked.get).toHaveBeenCalledWith('/gallery/tags');
    expect(mocked.post).toHaveBeenCalledWith('/gallery/tags', { name: 'Afro' });
    expect(result.current.items.map((t) => t.name)).toEqual(['Afro', 'Barba', 'Fade']);
  });
});

describe('sendPhoto', () => {
  it('manda o envio e devolve a foto gravada', async () => {
    const input = { image_url: 'https://exemplo.com/a.jpg', tag_ids: ['fade'] };
    mocked.post.mockResolvedValue({ data: NEW });

    expect(await sendPhoto(input)).toEqual(NEW);
    expect(mocked.post).toHaveBeenCalledWith('/gallery', input);
  });
});

describe('useGalleryModeration: carga', () => {
  it('carrega as pendentes e as publicadas', async () => {
    const { result } = await moderation();

    expect(mocked.get).toHaveBeenCalledWith('/gallery/pending');
    expect(mocked.get).toHaveBeenCalledWith('/gallery');
    expect(ids(result.current.pending.data)).toEqual(['p2', 'p1']);
    expect(ids(result.current.published.data)).toEqual(['p3']);
  });

  it('desligado (barbeiro), não chama a API', async () => {
    const { result } = renderHook(() => useGalleryModeration(false));

    await waitFor(() => expect(result.current.pending.status).toBe('ready'));
    expect(mocked.get).not.toHaveBeenCalled();
    expect(result.current.published.data).toEqual([]);
  });

  it('o 403 aparece no erro da carga', async () => {
    mocked.get.mockRejectedValue(httpError(403, 'Acesso restrito a administradores.'));
    const { result } = renderHook(() => useGalleryModeration(true));

    await waitFor(() => expect(result.current.pending.status).toBe('error'));
    expect(result.current.pending.loadError).toBe('Acesso restrito a administradores.');
  });
});

describe('useGalleryModeration: ações', () => {
  it('aprovar chama o PUT e move a foto para as publicadas, em ordem de data', async () => {
    const { result } = await moderation();
    mocked.put.mockResolvedValue({ data: { ...NEW, is_approved: true } });

    await act(() => result.current.approve('p2'));

    expect(mocked.put).toHaveBeenCalledWith('/gallery/p2/approve');
    expect(ids(result.current.pending.data)).toEqual(['p1']);
    expect(ids(result.current.published.data)).toEqual(['p2', 'p3']);
  });

  it('desaprovar chama o PUT e devolve a foto às pendentes', async () => {
    const { result } = await moderation();
    mocked.put.mockResolvedValue({ data: { ...LIVE, is_approved: false } });

    await act(() => result.current.unapprove('p3'));

    expect(mocked.put).toHaveBeenCalledWith('/gallery/p3/unapprove');
    expect(ids(result.current.pending.data)).toEqual(['p2', 'p3', 'p1']);
    expect(result.current.published.data).toEqual([]);
  });

  it('recusar manda o motivo e tira a foto das pendentes', async () => {
    const { result } = await moderation();
    mocked.put.mockResolvedValue({});

    await act(() => result.current.reject('p1', 'Foto desfocada'));

    expect(mocked.put).toHaveBeenCalledWith('/gallery/p1/reject', { reason: 'Foto desfocada' });
    expect(ids(result.current.pending.data)).toEqual(['p2']);
  });

  it('excluir chama o DELETE e tira a foto', async () => {
    const { result } = await moderation();
    mocked.delete.mockResolvedValue({});

    await act(() => result.current.remove('p3'));

    expect(mocked.delete).toHaveBeenCalledWith('/gallery/p3');
    expect(result.current.published.data).toEqual([]);
    expect(ids(result.current.pending.data)).toEqual(['p2', 'p1']);
  });

  it('a falha lança o erro da API e as listas não mudam', async () => {
    const { result } = await moderation();
    mocked.put.mockRejectedValue(httpError(400, 'A foto já foi aprovada.'));

    await expect(act(() => result.current.reject('p1', 'x'))).rejects.toThrow();
    expect(ids(result.current.pending.data)).toEqual(['p2', 'p1']);
  });

  it('place põe uma foto enviada na lista da situação dela', async () => {
    const { result } = await moderation();
    const sent = makePhoto('p4', { is_approved: true, created_at: '2026-11-25T10:00:00Z' });

    act(() => {
      result.current.place(sent);
    });

    expect(ids(result.current.published.data)).toEqual(['p4', 'p3']);
  });
});
