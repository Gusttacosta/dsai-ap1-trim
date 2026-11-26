// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import type { Expense } from '../hooks/useAdminExpenses';
import { ALUGUEL, LUZ, makeExpense } from '../testUtils/expenses';
import { httpError } from '../testUtils/httpError';
import { AMOUNT_ERROR } from '../utils/expenseValidation';
import { formatPrice } from '../utils/serviceValidation';
import AdminExpenses from './AdminExpenses';

// SPEC/2026-11-26-painel-despesas.md: a tela de despesas do painel, com a API simulada.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock; put: Mock; delete: Mock };

const RENT = makeExpense('e1', { description: 'Aluguel de novembro', amount: '1500.00', payment_date: '2026-11-05' }, ALUGUEL);
const POWER = makeExpense('e2', { description: 'Conta de luz', amount: '230.50', payment_date: '2026-11-03' }, LUZ);
const COFFEE = makeExpense('e3', { description: 'Café', amount: '20.00', payment_date: '2026-11-01' });

/** A API simulada: as despesas (ou a falha) e as categorias. */
function serve(expenses: Expense[] | Error = [RENT, POWER, COFFEE]) {
  mocked.get.mockImplementation((url: string) => {
    if (url === '/expenses/categories') return Promise.resolve({ data: [ALUGUEL, LUZ] });
    return expenses instanceof Error ? Promise.reject(expenses) : Promise.resolve({ data: expenses });
  });
}

async function renderPage(expenses: Expense[] = [RENT, POWER, COFFEE]) {
  serve(expenses);
  render(<AdminExpenses />);
  await screen.findByRole('row', { name: 'Aluguel' }); // a lista de categorias
  if (expenses.length) await screen.findByRole('row', { name: expenses[0].description });
}

const expenseCalls = () => mocked.get.mock.calls.filter(([url]) => url === '/expenses');
const row = (name: string) => screen.getByRole('row', { name });
const click = (name: string, scope: HTMLElement = document.body) =>
  fireEvent.click(within(scope).getByRole('button', { name }));
const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const total = () => screen.getByRole('status', { name: 'Total' }).textContent;

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});

afterEach(cleanup);

describe('AdminExpenses: lista e filtros', () => {
  it('carrega as despesas sem período e mostra o total', async () => {
    await renderPage();

    expect(expenseCalls()[0]).toEqual(['/expenses', { params: {} }]);
    expect(within(row('Conta de luz')).getByText('Luz')).toBeTruthy();
    expect(within(row('Café')).getByText('Sem categoria')).toBeTruthy();
    expect(total()).toBe(`Total: ${formatPrice(1750.5)}`);
  });

  it('o período vai para a API', async () => {
    await renderPage();
    serve([RENT]);

    type('De', '2026-11-04');
    type('Até', '2026-11-30');

    await waitFor(() =>
      expect(expenseCalls().at(-1)).toEqual(['/expenses', { params: { start_date: '2026-11-04', end_date: '2026-11-30' } }]),
    );
    await waitFor(() => expect(screen.queryByRole('row', { name: 'Café' })).toBeNull());
  });

  it('o período invertido mostra o 422 da API e "Tentar de novo"', async () => {
    await renderPage();
    serve(httpError(422, 'A data inicial não pode ser depois da data final.'));

    type('De', '2026-11-30');

    expect((await screen.findByRole('alert')).textContent).toBe('A data inicial não pode ser depois da data final.');
    expect(screen.getByRole('button', { name: 'Tentar de novo' })).toBeTruthy();
  });

  it('o filtro de categoria muda a lista e o total, sem chamar a API', async () => {
    await renderPage();
    const calls = expenseCalls().length;

    type('Filtrar por categoria', 'luz');
    expect(screen.getByRole('row', { name: 'Conta de luz' })).toBeTruthy();
    expect(screen.queryByRole('row', { name: 'Aluguel de novembro' })).toBeNull();
    expect(total()).toBe(`Total: ${formatPrice(230.5)}`);

    type('Filtrar por categoria', '__sem_categoria__');
    expect(screen.getByRole('row', { name: 'Café' })).toBeTruthy();
    expect(screen.queryByRole('row', { name: 'Conta de luz' })).toBeNull();
    expect(expenseCalls().length).toBe(calls);
  });

  it('sem despesas, avisa', async () => {
    await renderPage([]);

    expect(screen.getByText('Nenhuma despesa no período.')).toBeTruthy();
  });

  it('falha na carga mostra a mensagem e "Tentar de novo" carrega outra vez', async () => {
    serve(httpError(500));
    render(<AdminExpenses />);

    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível carregar as despesas.');
    serve([COFFEE]);
    click('Tentar de novo');

    expect(await screen.findByRole('row', { name: 'Café' })).toBeTruthy();
  });
});

describe('AdminExpenses: lançar, editar e excluir', () => {
  it('lança uma despesa, que entra na lista', async () => {
    await renderPage();
    const created = makeExpense('e4', { description: 'Internet', amount: '99.90', payment_date: '2026-11-04' });
    mocked.post.mockResolvedValue({ data: created });

    click('+ Nova Despesa');
    type('Descrição', 'Internet');
    type('Valor (R$)', '99,9');
    type('Data do pagamento', '2026-11-04');
    click('Salvar despesa');

    expect(await screen.findByText('Despesa lançada.')).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/expenses', {
      category_id: null,
      description: 'Internet',
      amount: '99.90',
      payment_date: '2026-11-04',
      is_recurring: false,
    });
    expect(screen.getByRole('row', { name: 'Internet' })).toBeTruthy();
    expect(screen.queryByRole('form', { name: 'Nova despesa' })).toBeNull();
  });

  it('valor inválido é recusado na tela, sem chamada', async () => {
    await renderPage();

    click('+ Nova Despesa');
    type('Descrição', 'Internet');
    type('Valor (R$)', '0');
    type('Data do pagamento', '2026-11-04');
    click('Salvar despesa');

    expect(screen.getByRole('alert').textContent).toBe(AMOUNT_ERROR);
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it('o 422 da API aparece no formulário, que continua aberto', async () => {
    await renderPage();
    mocked.post.mockRejectedValue(httpError(422, [{ msg: 'Input should be less than or equal to 99999999.99' }]));

    click('+ Nova Despesa');
    type('Descrição', 'Internet');
    type('Valor (R$)', '10');
    type('Data do pagamento', '2026-11-04');
    click('Salvar despesa');

    expect((await screen.findByRole('alert')).textContent).toBe('Input should be less than or equal to 99999999.99');
    expect(screen.getByRole('form', { name: 'Nova despesa' })).toBeTruthy();
  });

  it('editar manda só o que mudou e atualiza a linha', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...POWER, category: null, category_id: null } });

    click('Editar', row('Conta de luz'));
    type('Categoria', '');
    click('Salvar despesa');

    expect(await screen.findByText('Despesa atualizada.')).toBeTruthy();
    expect(mocked.put).toHaveBeenCalledWith('/expenses/e2', { category_id: null });
    expect(within(row('Conta de luz')).getByText('Sem categoria')).toBeTruthy();
  });

  it('excluir pede confirmação e tira a linha', async () => {
    await renderPage();
    mocked.delete.mockResolvedValue({});

    click('Excluir', row('Café'));
    expect(mocked.delete).not.toHaveBeenCalled();
    click('Confirmar', row('Café'));

    expect(await screen.findByText('Despesa excluída.')).toBeTruthy();
    expect(mocked.delete).toHaveBeenCalledWith('/expenses/e3');
    expect(screen.queryByRole('row', { name: 'Café' })).toBeNull();
  });

  it('a falha da exclusão mostra a mensagem da API e a linha continua', async () => {
    await renderPage();
    mocked.delete.mockRejectedValue(httpError(404, 'Despesa não encontrada.'));

    click('Excluir', row('Café'));
    click('Confirmar', row('Café'));

    expect((await screen.findByRole('alert')).textContent).toBe('Despesa não encontrada.');
    expect(row('Café')).toBeTruthy();
  });
});

describe('AdminExpenses: categorias', () => {
  it('excluir a categoria deixa as despesas dela "Sem categoria" e o filtro volta a "Todas"', async () => {
    await renderPage();
    mocked.delete.mockResolvedValue({});
    type('Filtrar por categoria', 'luz');

    const luz = within(screen.getByRole('region', { name: 'Categorias' })).getByRole('row', { name: 'Luz' });
    click('Excluir', luz);
    click('Confirmar', luz);

    expect(await screen.findByText('Categoria excluída.')).toBeTruthy();
    expect((screen.getByLabelText('Filtrar por categoria') as HTMLSelectElement).value).toBe('');
    expect(within(row('Conta de luz')).getByText('Sem categoria')).toBeTruthy();
    expect(expenseCalls().length).toBe(1);
  });

  it('renomear leva o nome novo às despesas', async () => {
    await renderPage();
    mocked.put.mockResolvedValue({ data: { ...ALUGUEL, name: 'Imóvel' } });

    const aluguel = within(screen.getByRole('region', { name: 'Categorias' })).getByRole('row', { name: 'Aluguel' });
    click('Renomear', aluguel);
    type('Novo nome de Aluguel', 'Imóvel');
    click('Salvar', aluguel);

    expect(await screen.findByText('Categoria renomeada.')).toBeTruthy();
    expect(within(row('Aluguel de novembro')).getByText('Imóvel')).toBeTruthy();
  });
});
