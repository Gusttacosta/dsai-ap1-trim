// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../../api';
import { httpError } from '../../testUtils/httpError';
import { makeSubscription } from '../../testUtils/trimClub';
import MySubscription, { CANCELED_NOTICE } from './MySubscription';

// SPEC/2026-11-26-painel-trim-club.md: a assinatura do cliente em "Minha conta".

vi.mock('../../api', () => ({ default: { get: vi.fn(), put: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; put: Mock };

function load(result: unknown) {
  mocked.get.mockImplementation(() => (result instanceof Error ? Promise.reject(result) : Promise.resolve({ data: result })));
  render(
    <MemoryRouter>
      <MySubscription />
    </MemoryRouter>,
  );
}

const section = () => within(screen.getByRole('region', { name: 'Trim Club' }));
const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));

beforeEach(() => {
  mocked.get.mockReset();
  mocked.put.mockReset();
});
afterEach(cleanup);

describe('MySubscription', () => {
  it('mostra o plano, os benefícios, a situação e a renovação', async () => {
    load(makeSubscription('s1'));

    expect(await screen.findByText('Ouro · R$ 150,00/mês')).toBeTruthy();
    expect(section().getByText('Cortes: Ilimitados')).toBeTruthy();
    expect(section().getByText('Barbas: 2 por mês')).toBeTruthy();
    expect(section().getByText('Desconto: 10%')).toBeTruthy();
    expect(section().getByText('Ativa')).toBeTruthy();
    expect(section().getByText('Renova em 26/12/2026.')).toBeTruthy();
    expect(mocked.get).toHaveBeenCalledWith('/subscriptions/me');
  });

  it('cancelar pede confirmação, chama o PUT e mostra a validade', async () => {
    load(makeSubscription('s1'));
    await screen.findByText('Renova em 26/12/2026.');
    mocked.put.mockResolvedValue({ data: makeSubscription('s1', { status: 'canceled' }) });

    click('Cancelar assinatura');
    expect(screen.getByText('Cancelar a assinatura? Os benefícios valem até 26/12/2026.')).toBeTruthy();
    expect(mocked.put).not.toHaveBeenCalled();
    click('Confirmar');

    expect(await screen.findByText(CANCELED_NOTICE)).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/subscriptions/me/cancel');
    expect(section().getByText('Cancelada. Seus benefícios valem até 26/12/2026.')).toBeTruthy();
    expect(section().getByText('Cancelada')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Cancelar assinatura' })).toBeNull();
  });

  it('"Voltar" desiste sem chamar a API', async () => {
    load(makeSubscription('s1'));
    await screen.findByText('Renova em 26/12/2026.');
    click('Cancelar assinatura');
    click('Voltar');
    expect(mocked.put).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Cancelar assinatura' })).toBeTruthy();
  });

  it('a falha do cancelamento mostra a mensagem da API, e a assinatura continua ativa', async () => {
    load(makeSubscription('s1'));
    await screen.findByText('Renova em 26/12/2026.');
    mocked.put.mockRejectedValue(httpError(400, 'Esta assinatura já está cancelada.'));

    click('Cancelar assinatura');
    click('Confirmar');

    expect((await screen.findByRole('alert')).textContent).toBe('Esta assinatura já está cancelada.');
    expect(section().getByText('Renova em 26/12/2026.')).toBeTruthy();
  });

  it('vencida mostra a data e o link para assinar de novo', async () => {
    load(makeSubscription('s1', { status: 'past_due', end_date: '2026-11-20' }));
    expect(await screen.findByText('Venceu em 20/11/2026.')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Assinar de novo' }).getAttribute('href')).toBe('/club');
    expect(screen.queryByRole('button', { name: 'Cancelar assinatura' })).toBeNull();
  });

  it('sem assinatura (404), convida para conhecer os planos', async () => {
    load(httpError(404, 'Você não possui uma assinatura.'));
    expect(await screen.findByText(/Você ainda não é sócio do Trim Club/)).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Conhecer os planos' }).getAttribute('href')).toBe('/club');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('outro erro mostra a mensagem e "Tentar de novo" carrega de novo', async () => {
    load(httpError(503, 'Banco fora do ar.'));
    expect((await screen.findByRole('alert')).textContent).toBe('Banco fora do ar.');

    mocked.get.mockResolvedValue({ data: makeSubscription('s1') });
    click('Tentar de novo');
    expect(await screen.findByText('Renova em 26/12/2026.')).toBeTruthy();
  });
});
