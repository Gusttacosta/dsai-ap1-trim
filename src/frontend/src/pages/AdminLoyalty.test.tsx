// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { DEACTIVATE_REWARD_QUESTION } from '../components/loyalty/RewardRow';
import { httpError } from '../testUtils/httpError';
import { ANA, BRUNO, CORTE, POMADA, makeRedemption, makeReward, walletResponse } from '../testUtils/loyalty';
import { ADJUST_REASON_ERROR, REWARD_NAME_ERROR } from '../utils/loyalty';
import AdminLoyalty from './AdminLoyalty';

// SPEC/2026-11-26-painel-fidelidade.md: a aba Fidelidade do painel, com a API simulada.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock };

const RESGATE = makeRedemption('r1', ANA, POMADA, '2026-11-26T17:30:00Z');

/** A API simulada; os prêmios, as carteiras ou os resgates podem ser um erro. */
function serve(rewards: unknown = [POMADA, CORTE], wallets: unknown = [ANA, BRUNO], redemptions: unknown = [RESGATE]) {
  const answer = (value: unknown) => (value instanceof Error ? Promise.reject(value) : Promise.resolve({ data: value }));
  const routes: Record<string, unknown> = {
    '/loyalty/rewards': rewards,
    '/loyalty/wallets': wallets,
    '/loyalty/redemptions': redemptions,
  };
  mocked.get.mockImplementation((url: string) => (url in routes ? answer(routes[url]) : Promise.reject(httpError(404))));
}

async function renderPage(...args: Parameters<typeof serve>) {
  serve(...args);
  render(<AdminLoyalty />);
  await screen.findByRole('row', { name: 'Corte grátis' });
  await screen.findByRole('row', { name: 'Ana Lima' });
}

const row = (name: string) => screen.getByRole('row', { name });
const click = (name: string, scope: HTMLElement = document.body) =>
  fireEvent.click(within(scope).getByRole('button', { name }));
const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const names = (table: string) =>
  within(screen.getByRole('table', { name: table }))
    .getAllByRole('row')
    .slice(1)
    .map((r) => r.getAttribute('aria-label'));
const REASON = 'Motivo (o cliente vê na notificação)';

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});
afterEach(cleanup);

describe('AdminLoyalty: prêmios', () => {
  it('lista os prêmios com o custo e a descrição', async () => {
    await renderPage();
    expect(names('Prêmios')).toEqual(['Pomada', 'Corte grátis']);
    expect(within(row('Corte grátis')).getByText('300 pts')).toBeTruthy();
    expect(within(row('Corte grátis')).getByText('Corte simples')).toBeTruthy();
  });

  it('cria um prêmio e o põe na lista, na ordem de custo', async () => {
    await renderPage();
    mocked.post.mockResolvedValue({ data: makeReward('barba', { name: 'Barba', description: 'Com toalha', points_cost: 200 }) });

    click('+ Novo prêmio');
    type('Nome', 'Barba');
    type('Custo (pontos)', '200');
    type('Descrição (opcional)', ' Com toalha ');
    click('Salvar prêmio');

    expect(await screen.findByText('Prêmio criado.')).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/loyalty/rewards', { name: 'Barba', description: 'Com toalha', points_cost: 200 });
    expect(names('Prêmios')).toEqual(['Pomada', 'Barba', 'Corte grátis']);
    expect(screen.queryByRole('form', { name: 'Novo prêmio' })).toBeNull();
  });

  it('edita só o que mudou e atualiza a linha', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...POMADA, points_cost: 500 } });

    click('Editar', row('Pomada'));
    type('Custo (pontos)', '500');
    click('Salvar prêmio');

    expect(await screen.findByText('Prêmio atualizado.')).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/loyalty/rewards/pomada', { points_cost: 500 });
    expect(names('Prêmios')).toEqual(['Corte grátis', 'Pomada']);
    expect(within(row('Pomada')).getByText('500 pts')).toBeTruthy();
  });

  it('nome vazio é recusado na tela, sem chamada', async () => {
    await renderPage();
    click('+ Novo prêmio');
    type('Custo (pontos)', '200');
    click('Salvar prêmio');
    expect((await screen.findByRole('alert')).textContent).toBe(REWARD_NAME_ERROR);
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it.each([
    [httpError(400, "Já existe um prêmio chamado 'Pomada'."), "Já existe um prêmio chamado 'Pomada'."],
    [httpError(422, [{ msg: 'String should have at most 150 characters' }]), 'String should have at most 150 characters'],
  ])('o erro da API aparece no formulário', async (error, message) => {
    await renderPage();
    mocked.post.mockRejectedValue(error);
    click('+ Novo prêmio');
    type('Nome', 'pomada');
    type('Custo (pontos)', '10');
    click('Salvar prêmio');
    expect((await screen.findByRole('alert')).textContent).toBe(message);
    expect(names('Prêmios')).toEqual(['Pomada', 'Corte grátis']);
  });

  it('desativar pede confirmação, manda is_active: false e tira o prêmio', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...CORTE, is_active: false } });

    click('Desativar', row('Corte grátis'));
    expect(within(row('Corte grátis')).getByText(DEACTIVATE_REWARD_QUESTION)).toBeTruthy();
    expect(mocked.put).not.toHaveBeenCalled();
    click('Confirmar', row('Corte grátis'));

    expect(await screen.findByText('Prêmio desativado. Ele saiu do catálogo.')).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/loyalty/rewards/corte', { is_active: false });
    expect(names('Prêmios')).toEqual(['Pomada']);
  });

  it('a falha ao desativar mostra a mensagem da API e o prêmio continua', async () => {
    await renderPage();
    mocked.put.mockRejectedValue(httpError(404, 'Prêmio não encontrado.'));
    click('Desativar', row('Corte grátis'));
    click('Confirmar', row('Corte grátis'));
    expect((await screen.findByRole('alert')).textContent).toBe('Prêmio não encontrado.');
    expect(names('Prêmios')).toEqual(['Pomada', 'Corte grátis']);
  });

  it('sem prêmios, diz que não há nenhum', async () => {
    serve([]);
    render(<AdminLoyalty />);
    expect(await screen.findByText('Nenhum prêmio cadastrado.')).toBeTruthy();
  });
});

describe('AdminLoyalty: carteiras', () => {
  it('lista as carteiras do maior saldo ao menor, com o saldo e o total acumulado', async () => {
    await renderPage();
    expect(names('Carteiras')).toEqual(['Ana Lima', 'Bruno Reis']);
    expect(within(row('Ana Lima')).getByText('120 pts')).toBeTruthy();
    expect(within(row('Ana Lima')).getByText('300 pts')).toBeTruthy();
  });

  it('o ajuste confirmado chama o /add com o motivo e atualiza o saldo', async () => {
    await renderPage();
    mocked.post.mockResolvedValue({ data: walletResponse(BRUNO, 240, 240) });

    click('Ajustar pontos', row('Bruno Reis'));
    type('Pontos', '200');
    type(REASON, ' Aniversário ');
    click('Ajustar pontos', screen.getByRole('form', { name: 'Ajustar pontos de Bruno Reis' }));

    expect(
      await screen.findByText('Adicionar 200 pts a Bruno Reis? O saldo passa de 40 para 240 pts. Motivo: Aniversário.'),
    ).toBeTruthy();
    expect(mocked.post).not.toHaveBeenCalled();
    click('Confirmar');

    expect(await screen.findByText('Pontos adicionados.')).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/loyalty/wallet/u2/add', null, {
      params: { points: 200, reason: 'Aniversário' },
    });
    expect(names('Carteiras')).toEqual(['Bruno Reis', 'Ana Lima']);
    expect(within(row('Bruno Reis')).getAllByText('240 pts')).toHaveLength(2);
    expect(screen.queryByRole('form', { name: 'Ajustar pontos de Bruno Reis' })).toBeNull();
  });

  it('retirar chama o /remove; o saldo insuficiente aparece e o saldo continua', async () => {
    await renderPage();
    const detail = 'Saldo insuficiente para retirar 500 pts. O cliente possui 120 pts.';
    mocked.post.mockRejectedValue(httpError(400, detail));

    click('Ajustar pontos', row('Ana Lima'));
    type('Operação', 'remove');
    type('Pontos', '500');
    type(REASON, 'Correção');
    click('Ajustar pontos', screen.getByRole('form', { name: 'Ajustar pontos de Ana Lima' }));
    click('Confirmar');

    expect((await screen.findByRole('alert')).textContent).toBe(detail);
    expect(mocked.post).toHaveBeenCalledWith('/loyalty/wallet/u1/remove', null, { params: { points: 500, reason: 'Correção' } });
    expect(within(row('Ana Lima')).getByText('120 pts')).toBeTruthy();
  });

  it('sem motivo, o ajuste é recusado sem pergunta nem chamada; "Voltar" não chama a API', async () => {
    await renderPage();
    click('Ajustar pontos', row('Ana Lima'));
    const form = screen.getByRole('form', { name: 'Ajustar pontos de Ana Lima' });
    type('Pontos', '50');
    click('Ajustar pontos', form);
    expect((await screen.findByRole('alert')).textContent).toBe(ADJUST_REASON_ERROR);

    type(REASON, 'Cortesia');
    click('Ajustar pontos', form);
    click('Voltar');
    click('Cancelar');
    expect(screen.queryByRole('form', { name: 'Ajustar pontos de Ana Lima' })).toBeNull();
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it('a falha na carga mostra a mensagem e "Tentar de novo" carrega de novo', async () => {
    serve(undefined, httpError(500, 'Erro no servidor.'));
    render(<AdminLoyalty />);
    expect(await screen.findByText('Erro no servidor.')).toBeTruthy();

    serve();
    click('Tentar de novo');
    expect(await screen.findByRole('row', { name: 'Ana Lima' })).toBeTruthy();
  });
});

describe('AdminLoyalty: resgates', () => {
  it('mostra a data, o nome do cliente, o prêmio e os pontos', async () => {
    await renderPage();
    const cells = within(screen.getByRole('table', { name: 'Resgates' })).getAllByRole('cell').map((c) => c.textContent);
    expect(cells).toEqual(['qui., 26/11/2026 às 14:30', 'Ana Lima', 'Pomada', '120 pts']);
  });

  it('a falha na carga mostra a mensagem da API', async () => {
    serve(undefined, undefined, httpError(403, 'Acesso restrito a administradores.'));
    render(<AdminLoyalty />);
    expect(await screen.findByText('Acesso restrito a administradores.')).toBeTruthy();
    await waitFor(() => expect(screen.getByRole('table', { name: 'Carteiras' })).toBeTruthy());
  });
});
