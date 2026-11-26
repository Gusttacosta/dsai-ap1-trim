// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { httpError, networkError } from '../testUtils/httpError';
import { PER_PAGE, useAdminUsers, type AdminUser, type UserFilters, type UserPage } from './useAdminUsers';

// SPEC/2026-11-25-admin-usuarios.md: a listagem paginada e as ações sobre um usuário.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock };

const user = (name: string, extra: Partial<AdminUser> = {}): AdminUser => ({
  id: name.toLowerCase(),
  email: `${name.toLowerCase()}@teste.com`,
  full_name: name,
  phone: null,
  role: 'client',
  is_active: true,
  email_verified: true,
  must_change_password: false,
  ...extra,
});

const ANA = user('Ana');
const BRUNO = user('Bruno', { role: 'barber' });
const page = (users: AdminUser[], extra: Partial<UserPage> = {}): UserPage => ({
  users,
  total: users.length,
  page: 1,
  per_page: PER_PAGE,
  total_pages: 1,
  ...extra,
});
const ALL: UserFilters = { q: '', role: '', page: 1 };

async function loaded(filters: UserFilters = ALL, data: UserPage = page([ANA, BRUNO])) {
  mocked.get.mockResolvedValue({ data });
  const hook = renderHook((f: UserFilters) => useAdminUsers(f), { initialProps: filters });
  await waitFor(() => expect(hook.result.current.status).toBe('ready'));
  return hook;
}

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

describe('useAdminUsers: carga', () => {
  it('pede a primeira página sem filtros', async () => {
    const { result } = await loaded();

    expect(mocked.get).toHaveBeenCalledWith('/auth/users', { params: { page: 1, per_page: PER_PAGE } });
    expect(result.current.users).toEqual([ANA, BRUNO]);
    expect(result.current.total_pages).toBe(1);
  });

  it('manda a busca sem espaços nas pontas, o perfil e a página', async () => {
    await loaded({ q: '  ana ', role: 'barber', page: 3 });

    expect(mocked.get).toHaveBeenCalledWith('/auth/users', {
      params: { page: 3, per_page: PER_PAGE, q: 'ana', role: 'barber' },
    });
  });

  it('mudar os filtros carrega de novo', async () => {
    const hook = await loaded();
    mocked.get.mockResolvedValue({ data: page([BRUNO]) });

    hook.rerender({ q: '', role: 'barber', page: 1 });

    await waitFor(() => expect(hook.result.current.users).toEqual([BRUNO]));
    expect(mocked.get).toHaveBeenCalledTimes(2);
  });

  it.each([
    ['a mensagem do backend', httpError(403, 'Acesso restrito para administradores.'), 'Acesso restrito para administradores.'],
    ['a mensagem padrão', httpError(500), 'Não foi possível carregar os usuários.'],
    ['sem conexão', networkError(), /Sem conexão/],
  ])('falha na carga mostra %s', async (_, error, expected) => {
    mocked.get.mockRejectedValue(error);
    const { result } = renderHook(() => useAdminUsers(ALL));

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.loadError).toMatch(expected);
  });
});

describe('useAdminUsers: ações', () => {
  it('changeRole usa a rota de perfil e mostra o usuário como o backend devolveu', async () => {
    const { result } = await loaded();
    mocked.put.mockResolvedValue({ data: { ...ANA, role: 'barber' } });

    await act(() => result.current.changeRole('ana', 'barber'));

    expect(mocked.put).toHaveBeenCalledWith('/auth/users/ana/role', { role: 'barber' });
    expect(result.current.users[0].role).toBe('barber');
    expect(result.current.users[1]).toEqual(BRUNO);
  });

  it('setActive usa a rota de situação', async () => {
    const { result } = await loaded();
    mocked.put.mockResolvedValue({ data: { ...ANA, is_active: false } });

    await act(() => result.current.setActive('ana', false));

    expect(mocked.put).toHaveBeenCalledWith('/auth/users/ana/status', { is_active: false });
    expect(result.current.users[0].is_active).toBe(false);
  });

  it('erro da ação é lançado e a lista não muda', async () => {
    const { result } = await loaded();
    mocked.put.mockRejectedValue(httpError(400, 'Você não pode desativar a sua própria conta.'));

    await expect(result.current.setActive('ana', false)).rejects.toThrow();
    expect(result.current.users).toEqual([ANA, BRUNO]);
  });

  it('generateTemporaryPassword devolve a senha e marca a troca pendente, sem guardar a senha', async () => {
    const { result } = await loaded();
    mocked.post.mockResolvedValue({ data: { temporary_password: 'Abc123def456', message: 'ok' } });

    let password = '';
    await act(async () => {
      password = await result.current.generateTemporaryPassword('ana');
    });

    expect(mocked.post).toHaveBeenCalledWith('/auth/users/ana/temporary-password');
    expect(password).toBe('Abc123def456');
    expect(result.current.users[0].must_change_password).toBe(true);
    expect(JSON.stringify(result.current)).not.toContain('Abc123def456');
  });

  it('erro ao gerar é lançado e o usuário não muda', async () => {
    const { result } = await loaded();
    mocked.post.mockRejectedValue(httpError(400, 'Ative a conta antes de gerar uma senha temporária.'));

    await expect(result.current.generateTemporaryPassword('ana')).rejects.toThrow();
    expect(result.current.users[0].must_change_password).toBe(false);
  });
});
