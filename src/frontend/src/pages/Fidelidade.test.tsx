// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import Fidelidade from './Fidelidade';

// SPEC/2026-11-25-fidelidade-pontos.md (#13): saldo, prêmios e resgate vêm da API.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }));
const mocked = api as unknown as { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };

const REWARDS = [
  { id: 'r1', name: 'Pomada', description: 'Efeito matte.', points_cost: 80 },
  { id: 'r2', name: 'Corte Grátis', description: null, points_cost: 150 },
];

function httpError(status: number, detail = ''): AxiosError {
  const config = { headers: {} } as InternalAxiosRequestConfig;
  const response = { status, data: { detail }, statusText: '', headers: {}, config } as AxiosResponse;
  return new AxiosError(`HTTP ${status}`, AxiosError.ERR_BAD_REQUEST, config, null, response);
}

function routes(wallet: unknown) {
  mocked.get.mockImplementation(async (url: string) => {
    if (url === '/loyalty/rewards') return { data: REWARDS };
    if (url === '/loyalty/me') {
      if (wallet instanceof Error) throw wallet;
      return { data: wallet };
    }
    throw new Error(`rota inesperada ${url}`);
  });
}

const renderPage = () =>
  render(
    <MemoryRouter>
      <Fidelidade />
    </MemoryRouter>,
  );

beforeEach(() => {
  mocked.get.mockReset();
  mocked.post.mockReset();
});

afterEach(cleanup);

describe('Fidelidade', () => {
  it('mostra o saldo real e os prêmios do catálogo', async () => {
    routes({ balance: 100, lifetime_points: 300 });
    renderPage();

    await waitFor(() => expect(screen.getByTestId('saldo').textContent).toContain('100'));
    expect(screen.getByText('Pomada')).toBeTruthy();
    expect(screen.getByText('Efeito matte.')).toBeTruthy();
    expect((screen.getByLabelText('Resgatar Pomada') as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByLabelText('Resgatar Corte Grátis') as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByLabelText('Resgatar Corte Grátis').textContent).toBe('Faltam pontos');
  });

  it('resgata pela API e recarrega o saldo', async () => {
    let balance = 100;
    mocked.get.mockImplementation(async (url: string) =>
      url === '/loyalty/rewards' ? { data: REWARDS } : { data: { balance, lifetime_points: 300 } },
    );
    mocked.post.mockImplementation(async () => {
      balance = 20;
      return { data: {} };
    });
    renderPage();

    fireEvent.click(await screen.findByLabelText('Resgatar Pomada'));

    expect((await screen.findByRole('status')).textContent).toContain('Você resgatou: Pomada');
    expect(mocked.post).toHaveBeenCalledWith('/loyalty/redeem/r1');
    await waitFor(() => expect(screen.getByTestId('saldo').textContent).toContain('20'));
  });

  it('mostra o erro do resgate', async () => {
    routes({ balance: 100, lifetime_points: 100 });
    mocked.post.mockRejectedValue(httpError(400, 'Saldo insuficiente. Você possui 10 pts e o prêmio custa 80 pts.'));
    renderPage();

    fireEvent.click(await screen.findByLabelText('Resgatar Pomada'));

    expect((await screen.findByRole('alert')).textContent).toBe(
      'Saldo insuficiente. Você possui 10 pts e o prêmio custa 80 pts.',
    );
  });

  it('sem login, mostra o catálogo e pede para entrar', async () => {
    routes(httpError(403));
    renderPage();

    expect(await screen.findByText('Entre na sua conta')).toBeTruthy();
    expect(screen.queryByTestId('saldo')).toBeNull();
    expect((screen.getByLabelText('Resgatar Pomada') as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByLabelText('Resgatar Pomada').textContent).toBe('Entre para resgatar');
  });

  it('não usa mais o saldo fixo de 120', async () => {
    routes({ balance: 0, lifetime_points: 0 });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('saldo').textContent).toContain('0'));
    expect(screen.getByTestId('saldo').textContent).not.toContain('120');
  });
});
