// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import type { Photo } from '../hooks/useGallery';
import { BARBA, CARLOS, FADE, JOAO, makePhoto } from '../testUtils/gallery';
import { httpError } from '../testUtils/httpError';
import { REASON_ERROR, TAG_NAME_ERROR } from '../utils/galleryValidation';
import AdminGallery, { PUBLISHED, SENT_FOR_REVIEW } from './AdminGallery';

// SPEC/2026-11-26-painel-galeria.md: a aba Galeria do painel, com a API simulada.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

const WAITING = makePhoto('p1', { description: 'Degradê do João', tags: [FADE] });
const LIVE = makePhoto('p2', { description: 'Barba do Carlos', barber_id: CARLOS.id, is_approved: true, tags: [BARBA] });

/** A API simulada; `pending` pode ser um erro. */
function serve(pending: Photo[] | Error = [WAITING], published: Photo[] = [LIVE]) {
  mocked.get.mockImplementation((url: string) => {
    if (url === '/gallery/tags') return Promise.resolve({ data: [BARBA, FADE] });
    if (url === '/barbers') return Promise.resolve({ data: [JOAO, CARLOS] });
    if (url === '/gallery/pending') {
      return pending instanceof Error ? Promise.reject(pending) : Promise.resolve({ data: pending });
    }
    return Promise.resolve({ data: published });
  });
}

async function renderAdmin() {
  serve();
  render(<AdminGallery isAdmin />);
  await screen.findByRole('row', { name: 'Degradê do João' });
  await screen.findByRole('row', { name: 'Barba do Carlos' });
  await screen.findByRole('row', { name: 'Fade' }); // a lista de tags
}

const requested = (url: string) => mocked.get.mock.calls.some(([called]) => called === url);
const table = (name: string) => screen.getByRole('table', { name });
const row = (name: string) => screen.getByRole('row', { name });
const click = (name: string, scope: HTMLElement = document.body) =>
  fireEvent.click(within(scope).getByRole('button', { name }));
const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

afterEach(cleanup);

describe('AdminGallery: permissões', () => {
  it('o barbeiro vê só o envio e não chama as rotas de admin', async () => {
    serve();
    render(<AdminGallery isAdmin={false} />);

    expect(await screen.findByRole('heading', { name: '📸 Galeria' })).toBeTruthy();
    await waitFor(() => expect(requested('/gallery/tags')).toBe(true));
    expect(screen.queryByRole('heading', { name: 'Pendentes' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Publicadas' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'Tags' })).toBeNull();
    expect(requested('/gallery/pending')).toBe(false);
    expect(requested('/gallery')).toBe(false);
  });

  it('o barbeiro envia sem barber_id e vê o aviso da aprovação', async () => {
    serve();
    render(<AdminGallery isAdmin={false} />);
    await waitFor(() => expect(screen.getByRole('button', { name: '+ Enviar foto' })).toHaveProperty('disabled', false));
    mocked.post.mockResolvedValue({ data: makePhoto('p9') });

    click('+ Enviar foto');
    expect(screen.queryByLabelText('Barbeiro')).toBeNull();
    type('URL da imagem', 'https://exemplo.com/novo.jpg');
    fireEvent.click(screen.getByLabelText('Fade'));
    click('Enviar foto');

    expect(await screen.findByText(SENT_FOR_REVIEW)).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/gallery', { image_url: 'https://exemplo.com/novo.jpg', tag_ids: ['fade'] });
    expect(screen.queryByRole('form', { name: 'Enviar foto' })).toBeNull();
  });

  it('o 404 do barbeiro sem perfil aparece no formulário', async () => {
    serve();
    render(<AdminGallery isAdmin={false} />);
    await waitFor(() => expect(screen.getByRole('button', { name: '+ Enviar foto' })).toHaveProperty('disabled', false));
    mocked.post.mockRejectedValue(httpError(404, 'Perfil de barbeiro não encontrado.'));

    click('+ Enviar foto');
    type('URL da imagem', 'https://exemplo.com/novo.jpg');
    click('Enviar foto');

    expect((await screen.findByRole('alert')).textContent).toBe('Perfil de barbeiro não encontrado.');
    expect(screen.getByRole('form', { name: 'Enviar foto' })).toBeTruthy();
  });
});

describe('AdminGallery: admin', () => {
  it('mostra as pendentes e as publicadas com o nome do barbeiro', async () => {
    await renderAdmin();

    expect(within(table('Pendentes')).getByText('João Silva')).toBeTruthy();
    expect(within(table('Publicadas')).getByText('Carlos Santos')).toBeTruthy();
    expect(within(row('Barba do Carlos')).getByText('Barba')).toBeTruthy();
  });

  it('o admin envia com o barbeiro escolhido e a foto entra nas publicadas', async () => {
    await renderAdmin();
    mocked.post.mockResolvedValue({ data: makePhoto('p9', { description: 'Novo corte', barber_id: CARLOS.id, is_approved: true }) });

    click('+ Enviar foto');
    type('URL da imagem', 'https://exemplo.com/novo.jpg');
    type('Barbeiro', CARLOS.id);
    click('Enviar foto');

    expect(await screen.findByText(PUBLISHED)).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/gallery', { image_url: 'https://exemplo.com/novo.jpg', tag_ids: [], barber_id: 'b2' });
    expect(within(table('Publicadas')).getByRole('row', { name: 'Novo corte' })).toBeTruthy();
  });

  it('aprovar move a foto para as publicadas', async () => {
    await renderAdmin();
    mocked.put.mockResolvedValue({ data: { ...WAITING, is_approved: true } });

    click('Aprovar', row('Degradê do João'));

    expect(await screen.findByText('Foto aprovada.')).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/gallery/p1/approve');
    expect(screen.getByText('Nenhuma foto pendente.')).toBeTruthy();
    expect(within(table('Publicadas')).getByRole('row', { name: 'Degradê do João' })).toBeTruthy();
  });

  it('desaprovar devolve a foto às pendentes', async () => {
    await renderAdmin();
    mocked.put.mockResolvedValue({ data: { ...LIVE, is_approved: false } });

    click('Desaprovar', row('Barba do Carlos'));

    expect(await screen.findByText('Nenhuma foto publicada.')).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/gallery/p2/unapprove');
    expect(within(table('Pendentes')).getByRole('row', { name: 'Barba do Carlos' })).toBeTruthy();
  });

  it('recusar pede o motivo, recusa o vazio e manda o motivo aparado', async () => {
    await renderAdmin();
    mocked.put.mockResolvedValue({});

    click('Recusar', row('Degradê do João'));
    click('Confirmar recusa', row('Degradê do João'));
    expect(screen.getByRole('alert').textContent).toBe(REASON_ERROR);
    expect(mocked.put).not.toHaveBeenCalled();

    type('Motivo da recusa', ' Foto desfocada ');
    click('Confirmar recusa', row('Degradê do João'));

    expect(await screen.findByText('Foto recusada. O barbeiro foi avisado.')).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/gallery/p1/reject', { reason: 'Foto desfocada' });
    expect(screen.queryByRole('row', { name: 'Degradê do João' })).toBeNull();
  });

  it('o 400 da recusa aparece no topo e a foto continua', async () => {
    await renderAdmin();
    mocked.put.mockRejectedValue(httpError(400, 'A foto já foi aprovada.'));

    click('Recusar', row('Degradê do João'));
    type('Motivo da recusa', 'Fora do padrão');
    click('Confirmar recusa', row('Degradê do João'));

    expect((await screen.findByRole('alert')).textContent).toBe('A foto já foi aprovada.');
    expect(row('Degradê do João')).toBeTruthy();
    expect(screen.getByLabelText('Motivo da recusa')).toBeTruthy();
  });

  it('excluir pede confirmação e tira a foto', async () => {
    await renderAdmin();
    mocked.delete.mockResolvedValue({});

    click('Excluir', row('Barba do Carlos'));
    expect(mocked.delete).not.toHaveBeenCalled();
    expect(within(row('Barba do Carlos')).getByText('Excluir a foto? Não dá para desfazer.')).toBeTruthy();
    click('Confirmar', row('Barba do Carlos'));

    expect(await screen.findByText('Foto excluída.')).toBeTruthy();
    expect(mocked.delete).toHaveBeenCalledWith('/gallery/p2');
    expect(screen.getByText('Nenhuma foto publicada.')).toBeTruthy();
  });

  it('a falha na exclusão mostra a mensagem da API e a foto continua', async () => {
    await renderAdmin();
    mocked.delete.mockRejectedValue(httpError(404, 'Imagem não encontrada.'));

    click('Excluir', row('Degradê do João'));
    click('Confirmar', row('Degradê do João'));

    expect((await screen.findByRole('alert')).textContent).toBe('Imagem não encontrada.');
    expect(row('Degradê do João')).toBeTruthy();
  });

  it('a falha na carga das pendentes mostra a mensagem e "Tentar de novo"', async () => {
    serve(httpError(500));
    render(<AdminGallery isAdmin />);

    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível carregar as fotos pendentes.');
    serve();
    click('Tentar de novo');

    expect(await screen.findByRole('row', { name: 'Degradê do João' })).toBeTruthy();
  });
});

describe('AdminGallery: tags', () => {
  const tagsSection = () => screen.getByRole('region', { name: 'Tags' });

  it('cria a tag com o nome aparado e a põe no formulário de envio', async () => {
    await renderAdmin();
    mocked.post.mockResolvedValue({ data: { id: 'afro', name: 'Afro' } });

    fireEvent.change(screen.getByLabelText('Nova tag'), { target: { value: ' Afro ' } });
    click('Adicionar', tagsSection());

    expect(await screen.findByText('Tag criada.')).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/gallery/tags', { name: 'Afro' });
    click('+ Enviar foto');
    expect(screen.getByRole('checkbox', { name: 'Afro' })).toBeTruthy();
  });

  it('nome com mais de 50 caracteres é recusado na tela', async () => {
    await renderAdmin();

    fireEvent.change(screen.getByLabelText('Nova tag'), { target: { value: 'a'.repeat(51) } });
    click('Adicionar', tagsSection());

    expect(within(tagsSection()).getByRole('alert').textContent).toBe(TAG_NAME_ERROR);
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it('nome repetido mostra o 400 da API', async () => {
    await renderAdmin();
    mocked.put.mockRejectedValue(httpError(400, "A tag 'Fade' já existe."));

    click('Renomear', row('Barba'));
    fireEvent.change(screen.getByLabelText('Novo nome de Barba'), { target: { value: 'Fade' } });
    click('Salvar', row('Barba'));

    expect((await within(tagsSection()).findByRole('alert')).textContent).toBe("A tag 'Fade' já existe.");
    expect(mocked.put).toHaveBeenCalledWith('/gallery/tags/barba', { name: 'Fade' });
  });

  it('excluir pede confirmação e chama o DELETE', async () => {
    await renderAdmin();
    mocked.delete.mockResolvedValue({});

    click('Excluir', row('Fade'));
    expect(screen.getByText('Excluir a tag? As fotos ficam sem ela.')).toBeTruthy();
    click('Confirmar', row('Fade'));

    expect(await screen.findByText('Tag excluída.')).toBeTruthy();
    expect(mocked.delete).toHaveBeenCalledWith('/gallery/tags/fade');
  });
});
