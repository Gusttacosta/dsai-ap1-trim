// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { httpError } from '../testUtils/httpError';
import ChangePasswordRequired from './ChangePasswordRequired';

// SPEC/2026-11-25-admin-usuarios.md: com a senha temporária, a pessoa troca a senha antes de entrar.

vi.mock('../api', () => ({ default: { get: vi.fn(), put: vi.fn() } }));
const mocked = api as unknown as { get: ReturnType<typeof vi.fn>; put: ReturnType<typeof vi.fn> };

const user = (role: string, must_change_password = true) => ({
  id: '1', email: 'ana@teste.com', full_name: 'Ana', phone: null, avatar_url: null,
  role, email_verified: true, must_change_password,
});

function renderPage() {
  render(
    <MemoryRouter initialEntries={['/trocar-senha']}>
      <Routes>
        <Route path="/trocar-senha" element={<ChangePasswordRequired />} />
        <Route path="/" element={<p>site</p>} />
        <Route path="/admin" element={<p>painel</p>} />
        <Route path="/login" element={<p>login</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });

function fillAndSubmit() {
  type('Senha atual', 'Temp1234abcd');
  type('Nova senha', 'senhaNova456');
  type('Confirme a nova senha', 'senhaNova456');
  fireEvent.click(screen.getByRole('button', { name: 'Trocar senha' }));
}

beforeEach(() => {
  mocked.get.mockReset();
  mocked.put.mockReset();
});

afterEach(cleanup);

describe('ChangePasswordRequired', () => {
  it('explica a troca e mostra o formulário', async () => {
    mocked.get.mockResolvedValue({ data: user('client') });
    renderPage();

    expect(await screen.findByRole('heading', { name: 'Troque sua senha' })).toBeTruthy();
    expect(screen.getByText(/senha temporária/)).toBeTruthy();
    expect(mocked.get).toHaveBeenCalledWith('/auth/me');
  });

  it.each([
    ['client', 'site'],
    ['barber', 'painel'],
    ['admin', 'painel'],
  ])('%s troca a senha e segue para a sua área', async (role, destination) => {
    mocked.get.mockResolvedValue({ data: user(role) });
    mocked.put.mockResolvedValue({ data: { message: 'Senha alterada.' } });
    renderPage();
    await screen.findByRole('heading', { name: 'Troque sua senha' });

    fillAndSubmit();

    expect(await screen.findByText(destination)).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/auth/me/password', {
      current_password: 'Temp1234abcd',
      new_password: 'senhaNova456',
    });
  });

  it('erro da troca aparece e a pessoa continua na tela', async () => {
    mocked.get.mockResolvedValue({ data: user('client') });
    mocked.put.mockRejectedValue(httpError(400, 'Senha atual incorreta.'));
    renderPage();
    await screen.findByRole('heading', { name: 'Troque sua senha' });

    fillAndSubmit();

    expect((await screen.findByRole('alert')).textContent).toBe('Senha atual incorreta.');
    expect(screen.queryByText('site')).toBeNull();
  });

  it('sem troca pendente, vai direto para a sua área', async () => {
    mocked.get.mockResolvedValue({ data: user('admin', false) });
    renderPage();
    expect(await screen.findByText('painel')).toBeTruthy();
  });

  it('sem sessão, vai para o login', async () => {
    mocked.get.mockRejectedValue(httpError(401));
    renderPage();
    expect(await screen.findByText('login')).toBeTruthy();
  });
});
