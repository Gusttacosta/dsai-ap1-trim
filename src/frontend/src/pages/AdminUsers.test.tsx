// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { PER_PAGE, type AdminUser } from '../hooks/useAdminUsers';
import { httpError } from '../testUtils/httpError';
import AdminUsers from './AdminUsers';

// SPEC/2026-11-25-admin-usuarios.md: a aba "Usuários" do painel do admin (#99).

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock };

const user = (id: string, full_name: string, extra: Partial<AdminUser> = {}): AdminUser => ({
  id,
  email: `${id}@teste.com`,
  full_name,
  phone: null,
  role: 'client',
  is_active: true,
  email_verified: true,
  must_change_password: false,
  ...extra,
});

const DONO = user('dono', 'Dono', { role: 'admin' });
const ANA = user('ana', 'Ana');
const BRUNO = user('bruno', 'Bruno', { role: 'barber', is_active: false });

const listing = (users: AdminUser[], extra = {}) => ({
  data: { users, total: users.length, page: 1, per_page: PER_PAGE, total_pages: 1, ...extra },
});

const row = (name: string) => screen.getByRole('row', { name });
const click = (name: string, scope: HTMLElement = document.body) =>
  fireEvent.click(within(scope).getByRole('button', { name }));
const lastParams = () => mocked.get.mock.lastCall?.[1].params;

async function renderPage(users: AdminUser[] = [DONO, ANA, BRUNO]) {
  mocked.get.mockResolvedValue(listing(users));
  render(<AdminUsers currentUserId="dono" />);
  if (users.length) await screen.findByRole('row', { name: users[0].full_name });
}

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

afterEach(cleanup);

describe('AdminUsers: listagem', () => {
  it('lista os usuários com perfil e situação, e o total', async () => {
    await renderPage();

    expect(mocked.get).toHaveBeenCalledWith('/auth/users', { params: { page: 1, per_page: PER_PAGE } });
    expect(screen.getByText('3 usuários')).toBeTruthy();
    expect((within(row('Ana')).getByRole('combobox') as HTMLSelectElement).value).toBe('client');
    expect(within(row('Bruno')).getByText('Desativado')).toBeTruthy();
  });

  it('a linha do próprio admin não tem ações', async () => {
    await renderPage();
    expect(within(row('Dono')).queryByRole('button')).toBeNull();
    expect(within(row('Dono')).getByText('Você')).toBeTruthy();
  });

  it('busca e filtro de perfil pedem a primeira página com os filtros', async () => {
    mocked.get.mockResolvedValue(listing([ANA], { total_pages: 3 }));
    render(<AdminUsers currentUserId="dono" />);
    await screen.findByRole('row', { name: 'Ana' });
    click('Próxima');
    await waitFor(() => expect(lastParams()).toMatchObject({ page: 2 }));

    fireEvent.change(screen.getByLabelText('Buscar por nome ou e-mail'), { target: { value: 'ana' } });
    click('Buscar');
    await waitFor(() => expect(lastParams()).toEqual({ page: 1, per_page: PER_PAGE, q: 'ana' }));

    fireEvent.change(screen.getByLabelText('Perfil'), { target: { value: 'barber' } });
    await waitFor(() => expect(lastParams()).toEqual({ page: 1, per_page: PER_PAGE, q: 'ana', role: 'barber' }));
  });

  it('a paginação mostra a página e pede a seguinte', async () => {
    mocked.get.mockResolvedValue(listing([ANA], { total: 45, page: 1, total_pages: 3 }));
    render(<AdminUsers currentUserId="dono" />);

    expect(await screen.findByText('Página 1 de 3')).toBeTruthy();
    click('Próxima');
    await waitFor(() => expect(lastParams()).toEqual({ page: 2, per_page: PER_PAGE }));
  });

  it('sem resultados, avisa', async () => {
    await renderPage([]);
    expect(await screen.findByText('Nenhum usuário encontrado.')).toBeTruthy();
  });

  it('falha na carga mostra o erro e "Tentar de novo" carrega outra vez', async () => {
    mocked.get.mockRejectedValueOnce(httpError(500)).mockResolvedValueOnce(listing([ANA]));
    render(<AdminUsers currentUserId="dono" />);

    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível carregar os usuários.');
    click('Tentar de novo');
    expect(await screen.findByRole('row', { name: 'Ana' })).toBeTruthy();
  });
});

describe('AdminUsers: ações', () => {
  it('trocar o perfil chama a API e mostra o perfil gravado', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...ANA, role: 'barber' } });

    fireEvent.change(within(row('Ana')).getByRole('combobox'), { target: { value: 'barber' } });

    expect((await screen.findByRole('status')).textContent).toBe('Ana agora é Barbeiro.');
    expect(mocked.put).toHaveBeenCalledWith('/auth/users/ana/role', { role: 'barber' });
    expect((within(row('Ana')).getByRole('combobox') as HTMLSelectElement).value).toBe('barber');
  });

  it('desativar pede confirmação e marca a conta', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...ANA, is_active: false } });

    click('Desativar', row('Ana'));
    expect(mocked.put).not.toHaveBeenCalled();
    click('Confirmar', row('Ana'));

    expect((await screen.findByRole('status')).textContent).toBe('Conta desativada.');
    expect(mocked.put).toHaveBeenCalledWith('/auth/users/ana/status', { is_active: false });
    expect(within(row('Ana')).getByText('Desativado')).toBeTruthy();
  });

  it('ativar chama a API sem confirmação', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...BRUNO, is_active: true } });

    click('Ativar', row('Bruno'));

    expect((await screen.findByRole('status')).textContent).toBe('Conta ativada.');
    expect(mocked.put).toHaveBeenCalledWith('/auth/users/bruno/status', { is_active: true });
  });

  it('erro da API aparece e a lista continua', async () => {
    await renderPage();
    mocked.put.mockRejectedValue(httpError(404, 'Usuário não encontrado.'));

    click('Desativar', row('Ana'));
    click('Confirmar', row('Ana'));

    expect((await screen.findByRole('alert')).textContent).toBe('Usuário não encontrado.');
    expect(within(row('Ana')).getByText('Ativo')).toBeTruthy();
  });

  it('gerar senha temporária mostra a senha uma vez; "Fechar" a tira da tela', async () => {
    await renderPage();
    mocked.post.mockResolvedValue({ data: { temporary_password: 'Abc123def456', message: 'ok' } });

    click('Gerar senha temporária', row('Ana'));
    click('Confirmar', row('Ana'));

    expect((await screen.findByLabelText('Senha temporária')).textContent).toBe('Abc123def456');
    expect(mocked.post).toHaveBeenCalledWith('/auth/users/ana/temporary-password');
    expect(screen.getByRole('heading', { name: 'Senha temporária de Ana' })).toBeTruthy();
    expect(within(row('Ana')).getByText('Troca de senha pendente')).toBeTruthy();

    click('Fechar');
    expect(screen.queryByText('Abc123def456')).toBeNull();
  });

  it('erro ao gerar a senha aparece e nenhum quadro é mostrado', async () => {
    await renderPage();
    mocked.post.mockRejectedValue(httpError(400, 'Ative a conta antes de gerar uma senha temporária.'));

    click('Gerar senha temporária', row('Ana'));
    click('Confirmar', row('Ana'));

    expect((await screen.findByRole('alert')).textContent).toBe('Ative a conta antes de gerar uma senha temporária.');
    expect(screen.queryByLabelText('Senha temporária')).toBeNull();
  });
});
