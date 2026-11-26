// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../../api';
import { PER_PAGE } from '../../hooks/useAdminUsers';
import { httpError } from '../../testUtils/httpError';
import UserPicker from './UserPicker';

// SPEC/2026-11-26-painel-barbeiros.md: a busca do usuário para criar um barbeiro.

vi.mock('../../api', () => ({ default: { get: vi.fn() } }));
const get = (api as unknown as { get: ReturnType<typeof vi.fn> }).get;

const user = (id: string, full_name: string) => ({
  id,
  email: `${id}@teste.com`,
  full_name,
  phone: null,
  role: 'client',
  is_active: true,
  email_verified: true,
  must_change_password: false,
});
const ANA = user('ana', 'Ana');
const BRUNO = user('bruno', 'Bruno');

const listing = (users: unknown[], total_pages = 1) => ({
  data: { users, total: users.length, page: 1, per_page: PER_PAGE, total_pages },
});

function renderPicker(barberUserIds: string[] = []) {
  const handlers = { onPick: vi.fn(), onCancel: vi.fn() };
  render(<UserPicker barberUserIds={new Set(barberUserIds)} {...handlers} />);
  return handlers;
}

beforeEach(() => {
  get.mockReset();
});
afterEach(cleanup);

describe('UserPicker', () => {
  it('busca na listagem de usuários, sem o filtro de perfil', async () => {
    get.mockResolvedValue(listing([ANA]));
    renderPicker();
    await screen.findByRole('row', { name: 'Ana' });
    expect(screen.queryByLabelText('Perfil')).toBeNull();

    fireEvent.change(screen.getByLabelText('Buscar por nome ou e-mail'), { target: { value: 'ana' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar' }));

    await waitFor(() =>
      expect(get).toHaveBeenLastCalledWith('/auth/users', { params: { page: 1, per_page: PER_PAGE, q: 'ana' } }),
    );
  });

  it('"Escolher" devolve o usuário; quem já é barbeiro não pode ser escolhido', async () => {
    get.mockResolvedValue(listing([ANA, BRUNO]));
    const { onPick } = renderPicker(['bruno']);

    const bruno = await screen.findByRole('row', { name: 'Bruno' });
    expect(within(bruno).queryByRole('button')).toBeNull();
    expect(within(bruno).getByText('Já é barbeiro')).toBeTruthy();

    fireEvent.click(within(screen.getByRole('row', { name: 'Ana' })).getByRole('button', { name: 'Escolher' }));
    expect(onPick).toHaveBeenCalledWith(ANA);
  });

  it('pagina a busca', async () => {
    get.mockResolvedValue(listing([ANA], 2));
    renderPicker();
    fireEvent.click(await screen.findByRole('button', { name: 'Próxima' }));
    await waitFor(() => expect(get.mock.lastCall?.[1].params.page).toBe(2));
  });

  it('sem resultado, diz isso; erro mostra a mensagem da API', async () => {
    get.mockResolvedValueOnce(listing([])).mockRejectedValueOnce(httpError(403, 'Acesso restrito a administradores.'));
    renderPicker();
    expect(await screen.findByText('Nenhum usuário encontrado.')).toBeTruthy();

    fireEvent.change(screen.getByLabelText('Buscar por nome ou e-mail'), { target: { value: 'x' } });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar' }));
    expect((await screen.findByRole('alert')).textContent).toBe('Acesso restrito a administradores.');
  });

  it('"Cancelar" fecha', async () => {
    get.mockResolvedValue(listing([]));
    const { onCancel } = renderPicker();
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onCancel).toHaveBeenCalled();
  });
});
