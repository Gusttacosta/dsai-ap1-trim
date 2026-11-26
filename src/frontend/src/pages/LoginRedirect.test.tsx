// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { ComponentType } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import Login from './Login';
import LoginAdmin from './LoginAdmin';

// SPEC/2026-11-25-admin-usuarios.md: no login do cliente e no profissional, quem está com a
// senha temporária vai para a troca de senha antes de entrar.

vi.mock('../api', () => ({ default: { post: vi.fn() } }));
const mockedPost = api.post as unknown as ReturnType<typeof vi.fn>;

function renderLogin(Page: ComponentType) {
  render(
    <MemoryRouter initialEntries={['/entrar']}>
      <Routes>
        <Route path="/entrar" element={<Page />} />
        <Route path="/trocar-senha" element={<p>troca de senha</p>} />
        <Route path="/" element={<p>site</p>} />
        <Route path="/admin" element={<p>painel</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

function submit(role: string, must_change_password: boolean) {
  mockedPost.mockResolvedValue({ data: { access_token: 'tok', user: { role, must_change_password } } });
  fireEvent.change(screen.getByPlaceholderText('E-mail'), { target: { value: 'ana@teste.com' } });
  fireEvent.change(screen.getByPlaceholderText('Senha'), { target: { value: 'Temp1234abcd' } });
  fireEvent.submit(screen.getByPlaceholderText('Senha').closest('form')!);
}

beforeEach(() => {
  mockedPost.mockReset();
  localStorage.clear();
});

afterEach(cleanup);

describe.each([
  ['Login (cliente)', Login, 'client', 'site'],
  ['LoginAdmin (admin)', LoginAdmin, 'admin', 'painel'],
  ['LoginAdmin (barbeiro)', LoginAdmin, 'barber', 'painel'],
] as const)('%s', (_, Page, role, home) => {
  it('com a troca pendente, vai para a troca de senha', async () => {
    renderLogin(Page);
    submit(role, true);

    expect(await screen.findByText('troca de senha')).toBeTruthy();
    expect(localStorage.getItem('token')).toBe('tok');
  });

  it('sem a troca pendente, entra normalmente', async () => {
    renderLogin(Page);
    submit(role, false);

    expect(await screen.findByText(home)).toBeTruthy();
  });
});
