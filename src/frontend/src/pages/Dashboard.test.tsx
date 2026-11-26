// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import Dashboard from './Dashboard';

// SPEC/2026-11-25-admin-usuarios.md: a aba "Usuários" existe só para o admin, e quem está com a
// senha temporária troca a senha antes de usar o painel.

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

const requested = (url: string) => mockedGet.mock.calls.some(([called]) => called === url);

// SPEC/2026-11-26-painel-barbeiros.md, SPEC/2026-11-26-painel-despesas.md,
// SPEC/2026-11-26-painel-trim-club.md, SPEC/2026-11-26-painel-fidelidade.md e
// SPEC/2026-11-26-painel-estoque.md: as abas "Barbeiros", "Despesas", "Trim Club", "Fidelidade"
// e "Loja & Estoque" seguem a mesma regra.
describe.each([
  ['Usuários', '👥 Usuários', '/admin/usuarios', '/auth/users'],
  ['Barbeiros', '💈 Barbeiros', '/admin/barbeiros', '/barbers/admin'],
  ['Despesas', '💸 Despesas', '/admin/despesas', '/expenses'],
  ['Trim Club', '👑 Trim Club', '/admin/trim-club', '/subscriptions/users'],
  ['Fidelidade', '🎁 Fidelidade', '/admin/fidelidade', '/loyalty/wallets'],
  ['Loja & Estoque', '📦 Loja & Estoque', '/admin/loja', '/products/admin/all'],
])('Dashboard: aba %s', (link, heading, path, apiUrl) => {
  it(`o admin vê o item no menu e a tela em ${path}`, async () => {
    renderAt(path, me('admin'));

    expect(await screen.findByRole('link', { name: link })).toBeTruthy();
    expect(await screen.findByRole('heading', { name: heading })).toBeTruthy();
    expect(requested(apiUrl)).toBe(true);
  });

  it.each(['barber', 'client'])('o perfil %s não vê o item nem a tela', async (role) => {
    renderAt(path, me(role));

    expect(await screen.findByRole('link', { name: 'Minha conta' })).toBeTruthy();
    expect(screen.queryByRole('link', { name: link })).toBeNull();
    expect(screen.queryByRole('heading', { name: heading })).toBeNull();
    expect(requested(apiUrl)).toBe(false);
  });
});

// SPEC/2026-11-26-painel-galeria.md: a aba "Galeria" é do admin e do barbeiro, que enviam fotos;
// a moderação (/gallery/pending) é só do admin.
describe('Dashboard: aba Galeria', () => {
  it.each([
    ['admin', true],
    ['barber', false],
  ])('o %s vê o item no menu e a tela em /admin/galeria', async (role, moderates) => {
    renderAt('/admin/galeria', me(role));

    expect(await screen.findByRole('link', { name: 'Galeria' })).toBeTruthy();
    expect(await screen.findByRole('heading', { name: '📸 Galeria' })).toBeTruthy();
    expect(requested('/gallery/pending')).toBe(moderates);
  });

  it('o cliente não vê o item nem a tela', async () => {
    renderAt('/admin/galeria', me('client'));

    expect(await screen.findByRole('link', { name: 'Minha conta' })).toBeTruthy();
    expect(screen.queryByRole('link', { name: 'Galeria' })).toBeNull();
    expect(screen.queryByRole('heading', { name: '📸 Galeria' })).toBeNull();
    expect(requested('/gallery/tags')).toBe(false);
  });
});

describe('Dashboard: senha temporária', () => {
  it('com a troca pendente, manda para a troca de senha', async () => {
    renderAt('/admin', me('admin', { must_change_password: true }));

    expect(await screen.findByText('tela de troca')).toBeTruthy();
    expect(screen.queryByRole('link', { name: 'Usuários' })).toBeNull();
  });
});
