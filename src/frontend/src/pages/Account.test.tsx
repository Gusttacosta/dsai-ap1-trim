// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { makeSubscription } from '../testUtils/trimClub';
import Account from './Account';

// SPEC/2026-11-22-auth-perfil-senha.md: a página carrega o /auth/me e usa as duas rotas novas.

vi.mock('../api', () => ({ default: { get: vi.fn(), put: vi.fn() } }));
const mocked = api as unknown as { get: ReturnType<typeof vi.fn>; put: ReturnType<typeof vi.fn> };

const USER = {
  id: '1',
  email: 'cliente@teste.com',
  full_name: 'maria',
  phone: null,
  avatar_url: null,
  role: 'client',
  email_verified: false,
};

const APPOINTMENT = {
  id: 'a1',
  barber_id: 'b1',
  start_datetime: '2099-12-02T13:00:00Z',
  end_datetime: '2099-12-02T13:30:00Z',
  status: 'confirmed',
  total_price: '40.00',
  items: [{ id: 'i1', service_name: 'Corte', locked_price: '40.00', duration_minutes: 30 }],
};

function httpError(status: number): AxiosError {
  const config = { headers: {} } as InternalAxiosRequestConfig;
  const response = { status, data: {}, statusText: '', headers: {}, config } as AxiosResponse;
  return new AxiosError(`HTTP ${status}`, AxiosError.ERR_BAD_REQUEST, config, null, response);
}

/** A API simulada: o /auth/me com `user`, as rotas de `routes` e, nas outras, a conta sem
 * agendamentos e sem assinatura (404 no /subscriptions/me). */
function serve(user: object, routes: Record<string, unknown> = {}) {
  mocked.get.mockImplementation(async (url: string) => {
    if (url === '/auth/me') return { data: user };
    if (url in routes) return { data: routes[url] };
    if (url === '/subscriptions/me') throw httpError(404);
    return { data: [] };
  });
}

function renderAccount() {
  return render(
    <MemoryRouter initialEntries={['/conta']}>
      <Routes>
        <Route path="/conta" element={<Account loginPath="/login" />} />
        <Route path="/login" element={<p>Tela de login</p>} />
        <Route path="/trocar-senha" element={<p>Tela de troca de senha</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mocked.get.mockReset();
  mocked.put.mockReset();
});

afterEach(cleanup);

describe('Account', () => {
  it('mostra os dados do usuário, o perfil e o aviso de e-mail não verificado', async () => {
    mocked.get.mockResolvedValue({ data: USER });

    renderAccount();

    expect(await screen.findByRole('heading', { name: 'Minha conta' })).toBeTruthy();
    expect(screen.getByText('cliente@teste.com · Cliente')).toBeTruthy();
    expect(screen.getByText('Seu e-mail ainda não foi verificado.')).toBeTruthy();
    expect(screen.getByText('M')).toBeTruthy();
    expect(mocked.get).toHaveBeenCalledWith('/auth/me');
  });

  it('o cliente vê "Meus agendamentos", carregado do GET /appointments/me (SPEC/2026-11-25-meus-agendamentos.md)', async () => {
    serve(USER, { '/appointments/me': [APPOINTMENT] });

    renderAccount();

    expect(await screen.findByRole('heading', { name: 'Meus agendamentos' })).toBeTruthy();
    expect(await screen.findByRole('listitem', { name: /Corte$/ })).toBeTruthy();
    expect(mocked.get).toHaveBeenCalledWith('/appointments/me');
  });

  it('o cliente vê a assinatura do Trim Club, carregada do GET /subscriptions/me (SPEC/2026-11-26-painel-trim-club.md)', async () => {
    serve(USER, { '/subscriptions/me': makeSubscription('s1') });

    renderAccount();

    expect(await screen.findByRole('heading', { name: 'Trim Club' })).toBeTruthy();
    expect(await screen.findByText('Renova em 26/12/2026.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Cancelar assinatura' })).toBeTruthy();
  });

  it('o cliente sem assinatura vê o convite para os planos', async () => {
    serve(USER);

    renderAccount();

    expect(await screen.findByText(/Você ainda não é sócio do Trim Club/)).toBeTruthy();
  });

  it.each(['barber', 'admin'])('%s não vê "Meus agendamentos" nem o Trim Club, e não chama as rotas', async (role) => {
    serve({ ...USER, role });

    renderAccount();

    expect(await screen.findByRole('heading', { name: 'Minha conta' })).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'Meus agendamentos' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Trim Club' })).toBeNull();
    expect(mocked.get).not.toHaveBeenCalledWith('/appointments/me');
    expect(mocked.get).not.toHaveBeenCalledWith('/subscriptions/me');
  });

  it.each([401, 403])('sem sessão (%i), manda para o login', async (status) => {
    mocked.get.mockRejectedValue(httpError(status));

    renderAccount();

    expect(await screen.findByText('Tela de login')).toBeTruthy();
  });

  it('outros erros aparecem na tela', async () => {
    mocked.get.mockRejectedValue(httpError(500));

    renderAccount();

    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Não foi possível carregar seus dados.');
  });

  it('salva o perfil pelo PUT /auth/me e mostra o telefone como o backend gravou', async () => {
    serve(USER);
    mocked.put.mockResolvedValue({ data: { ...USER, phone: '(91) 99999-0000' } });
    renderAccount();

    fireEvent.change(await screen.findByLabelText('Telefone'), { target: { value: '91 99999 0000' } });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar dados' }));

    expect(await screen.findByText('Dados salvos.')).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/auth/me', { phone: '(91) 99999-0000' });
    expect(screen.getByLabelText('Telefone')).toHaveProperty('value', '(91) 99999-0000');
  });

  it('troca a senha pelo PUT /auth/me/password', async () => {
    serve(USER);
    mocked.put.mockResolvedValue({ data: { message: 'Senha alterada. As outras sessões foram encerradas.' } });
    renderAccount();

    fireEvent.change(await screen.findByLabelText('Senha atual'), { target: { value: 'senhaAtual1' } });
    fireEvent.change(screen.getByLabelText('Nova senha'), { target: { value: 'senhaNova2' } });
    fireEvent.change(screen.getByLabelText('Confirme a nova senha'), { target: { value: 'senhaNova2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Trocar senha' }));

    expect(await screen.findByText('Senha alterada. As outras sessões foram encerradas.')).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/auth/me/password', {
      current_password: 'senhaAtual1',
      new_password: 'senhaNova2',
    });
  });
});

describe('Account: senha temporária (SPEC/2026-11-25-admin-usuarios.md)', () => {
  it('com a troca pendente, manda para a troca de senha', async () => {
    mocked.get.mockResolvedValue({ data: { ...USER, must_change_password: true } });
    renderAccount();

    expect(await screen.findByText('Tela de troca de senha')).toBeTruthy();
    expect(mocked.get).not.toHaveBeenCalledWith('/appointments/me');
    expect(mocked.get).not.toHaveBeenCalledWith('/subscriptions/me');
  });
});
