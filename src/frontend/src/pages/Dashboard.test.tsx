// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import Dashboard from './Dashboard';

// SPEC/2026-11-25-admin-usuarios.md: a aba "Usuários" existe só para o admin.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, logout: vi.fn() }));
const mockedGet = api.get as unknown as ReturnType<typeof vi.fn>;

const me = (role: string, extra = {}) => ({
  id: 'u1', email: 'u1@teste.com', full_name: 'Pessoa', role, must_change_password: false, ...extra,
});

function renderAt(path: string, user: object) {
  mockedGet.mockImplementation((url: string) => {
    if (url === '/auth/me') return Promise.resolve({ data: user });
    if (url === '/auth/users') {
      return Promise.resolve({ data: { users: [], total: 0, page: 1, per_page: 20, total_pages: 0 } });
    }
    return Promise.resolve({ data: [] });
  });
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/*" element={<Dashboard />} />
        <Route path="/trocar-senha" element={<p>tela de troca</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => mockedGet.mockReset());
afterEach(cleanup);

describe('Dashboard: aba Usuários', () => {
  it('o admin vê o item no menu e a tela em /admin/usuarios', async () => {
    renderAt('/admin/usuarios', me('admin'));

    expect(await screen.findByRole('link', { name: 'Usuários' })).toBeTruthy();
    expect(await screen.findByRole('heading', { name: '👥 Usuários' })).toBeTruthy();
    expect(mockedGet).toHaveBeenCalledWith('/auth/users', expect.anything());
  });

  it('o barbeiro não vê o item nem a tela', async () => {
    renderAt('/admin/usuarios', me('barber'));

    expect(await screen.findByRole('link', { name: 'Minha conta' })).toBeTruthy();
    expect(screen.queryByRole('link', { name: 'Usuários' })).toBeNull();
    expect(screen.queryByRole('heading', { name: '👥 Usuários' })).toBeNull();
    expect(mockedGet).not.toHaveBeenCalledWith('/auth/users', expect.anything());
  });
});
