// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { DELETE_PLAN_QUESTION } from '../components/trimClub/PlanRow';
import { httpError } from '../testUtils/httpError';
import { BASICO, OURO, makePlan, makeSubscription } from '../testUtils/trimClub';
import { PLAN_NAME_ERROR } from '../utils/trimClub';
import AdminTrimClub from './AdminTrimClub';

// SPEC/2026-11-26-painel-trim-club.md: a aba Trim Club do painel, com a API simulada.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

const ANA = makeSubscription('s1', { user_id: 'u1' });

/** A API simulada; os planos ou os assinantes podem ser um erro. */
function serve(plans: unknown = [BASICO, OURO], subscriptions: unknown = [ANA]) {
  const answer = (value: unknown) => (value instanceof Error ? Promise.reject(value) : Promise.resolve({ data: value }));
  mocked.get.mockImplementation((url: string) => {
    if (url === '/subscriptions/plans') return answer(plans);
    if (url === '/subscriptions/users') return answer(subscriptions);
    if (url === '/auth/users/u1') return answer({ full_name: 'Ana Souza', email: 'ana@x.com' });
    return Promise.reject(httpError(404));
  });
}

async function renderPage() {
  serve();
  render(<AdminTrimClub />);
  await screen.findByRole('row', { name: 'Ouro' });
  await screen.findByRole('row', { name: 'Ana Souza' });
}

const row = (name: string) => screen.getByRole('row', { name });
const click = (name: string, scope: HTMLElement = document.body) =>
  fireEvent.click(within(scope).getByRole('button', { name }));
const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const planNames = () =>
  within(screen.getByRole('table', { name: 'Planos' }))
    .getAllByRole('row')
    .slice(1)
    .map((r) => r.getAttribute('aria-label'));

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});
afterEach(cleanup);

describe('AdminTrimClub: planos', () => {
  it('lista os planos com preço e benefícios', async () => {
    await renderPage();

    expect(planNames()).toEqual(['Básico', 'Ouro']);
    expect(within(row('Ouro')).getByText('R$ 150,00/mês')).toBeTruthy();
    expect(within(row('Ouro')).getByText('Cortes: Ilimitados · Barbas: 2 por mês · Desconto: 10%')).toBeTruthy();
    expect(within(row('Ouro')).getByText('Bebida premium')).toBeTruthy();
  });

  it('cria um plano e o põe na lista, na ordem de preço', async () => {
    await renderPage();
    const prata = makePlan('prata', { name: 'Prata', monthly_price: '89.90', included_cuts: 4 });
    mocked.post.mockResolvedValue({ data: prata });

    click('+ Novo plano');
    type('Nome', 'Prata');
    type('Preço mensal (R$)', '89,90');
    type('Cortes inclusos', '4');
    click('Salvar plano');

    expect(await screen.findByText('Plano criado.')).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/subscriptions/plans', {
      name: 'Prata',
      description: null,
      monthly_price: '89.90',
      included_cuts: 4,
      included_shaves: 0,
      discount_percentage: '0.00',
    });
    expect(planNames()).toEqual(['Básico', 'Prata', 'Ouro']);
    expect(screen.queryByRole('form', { name: 'Novo plano' })).toBeNull();
  });

  it('nome vazio é recusado na tela, sem chamar a API', async () => {
    await renderPage();
    click('+ Novo plano');
    type('Preço mensal (R$)', '10');
    click('Salvar plano');

    expect(within(screen.getByRole('form', { name: 'Novo plano' })).getByRole('alert').textContent).toBe(PLAN_NAME_ERROR);
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it('o 422 da API aparece no formulário, que continua aberto', async () => {
    await renderPage();
    mocked.post.mockRejectedValue(httpError(422, [{ msg: 'Input should be greater than 0' }]));

    click('+ Novo plano');
    type('Nome', 'Prata');
    type('Preço mensal (R$)', '10');
    click('Salvar plano');

    const form = screen.getByRole('form', { name: 'Novo plano' });
    expect((await within(form).findByRole('alert')).textContent).toBe('Input should be greater than 0');
  });

  it('edita só o que mudou e atualiza a linha', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...BASICO, monthly_price: '59.90' } });

    click('Editar', row('Básico'));
    type('Preço mensal (R$)', '59,90');
    click('Salvar plano');

    expect(await screen.findByText('Plano atualizado.')).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/subscriptions/plans/basico', { monthly_price: '59.90' });
    expect(within(row('Básico')).getByText('R$ 59,90/mês')).toBeTruthy();
  });

  it('o nome repetido na edição mostra o 400 da API', async () => {
    await renderPage();
    mocked.put.mockRejectedValue(httpError(400, 'Já existe um plano com esse nome.'));

    click('Editar', row('Básico'));
    type('Nome', 'ouro');
    click('Salvar plano');

    const form = screen.getByRole('form', { name: 'Editar plano' });
    expect((await within(form).findByRole('alert')).textContent).toBe('Já existe um plano com esse nome.');
  });

  it('excluir pede confirmação, chama o DELETE e tira o plano', async () => {
    await renderPage();
    mocked.delete.mockResolvedValue({ data: null });

    click('Excluir', row('Ouro'));
    expect(within(row('Ouro')).getByText(DELETE_PLAN_QUESTION)).toBeTruthy();
    expect(mocked.delete).not.toHaveBeenCalled();
    click('Confirmar', row('Ouro'));

    expect(await screen.findByText('Plano excluído. Ele saiu da vitrine.')).toBeTruthy();
    expect(mocked.delete).toHaveBeenCalledWith('/subscriptions/plans/ouro');
    expect(planNames()).toEqual(['Básico']);
  });

  it('a falha da exclusão mostra a mensagem da API, e o plano continua', async () => {
    await renderPage();
    mocked.delete.mockRejectedValue(httpError(404, 'Plano não encontrado.'));

    click('Excluir', row('Ouro'));
    click('Confirmar', row('Ouro'));

    expect((await screen.findByRole('alert')).textContent).toBe('Plano não encontrado.');
    expect(planNames()).toEqual(['Básico', 'Ouro']);
  });

  it('sem planos, diz que não há plano cadastrado', async () => {
    serve([], []);
    render(<AdminTrimClub />);
    expect(await screen.findByText('Nenhum plano cadastrado.')).toBeTruthy();
    expect(await screen.findByText('Nenhum assinante ainda.')).toBeTruthy();
  });

  it('a falha na carga dos planos mostra a mensagem e "Tentar de novo"', async () => {
    serve(httpError(500));
    render(<AdminTrimClub />);
    expect(await screen.findByText('Não foi possível carregar os planos.')).toBeTruthy();
    expect(screen.getByRole('button', { name: '+ Novo plano' })).toHaveProperty('disabled', true);

    serve();
    click('Tentar de novo');
    expect(await screen.findByRole('row', { name: 'Ouro' })).toBeTruthy();
  });
});

describe('AdminTrimClub: assinantes', () => {
  it('mostra o cliente, o plano, as datas e a situação', async () => {
    await renderPage();
    const ana = within(row('Ana Souza'));
    expect(ana.getByText('ana@x.com')).toBeTruthy();
    expect(ana.getByText('Ouro')).toBeTruthy();
    expect(ana.getByText('26/12/2026')).toBeTruthy();
    expect(ana.getByText('Ativa')).toBeTruthy();
  });

  it('a falha na carga mostra a mensagem da API e "Tentar de novo"', async () => {
    serve([BASICO], httpError(403, 'Acesso restrito a administradores.'));
    render(<AdminTrimClub />);
    expect(await screen.findByText('Acesso restrito a administradores.')).toBeTruthy();

    serve();
    click('Tentar de novo');
    await waitFor(() => expect(screen.getByRole('row', { name: 'Ana Souza' })).toBeTruthy());
  });
});
