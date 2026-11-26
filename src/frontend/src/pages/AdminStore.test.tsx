// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { httpError } from '../testUtils/httpError';
import { OLEO, PENTE, POMADA, SHAMPOO, makeMovement } from '../testUtils/inventory';
import { QUANTITY_ERROR } from '../utils/inventory';
import AdminStore from './AdminStore';

// SPEC/2026-11-26-painel-estoque.md: a aba Loja & Estoque do painel, com a API simulada.

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock };

const ENTRADA = makeMovement('m1', POMADA, { quantity: 3, notes: 'Nota 12' });

/** A API simulada; os produtos ou o histórico podem ser um erro. */
function serve(products: unknown = [OLEO, PENTE, POMADA, SHAMPOO], history: unknown = [ENTRADA]) {
  const answer = (value: unknown) => (value instanceof Error ? Promise.reject(value) : Promise.resolve({ data: value }));
  mocked.get.mockImplementation((url: string) => {
    if (url === '/products/admin/all') return answer(products);
    if (url.endsWith('/inventory')) return answer(history);
    return Promise.reject(httpError(404));
  });
}

async function renderPage(...args: Parameters<typeof serve>) {
  serve(...args);
  render(<AdminStore />);
  await screen.findByRole('row', { name: 'Pomada' });
}

const row = (name: string) => screen.getByRole('row', { name });
const click = (name: string, scope: HTMLElement = document.body) =>
  fireEvent.click(within(scope).getByRole('button', { name }));
const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const stock = (name: string) => within(row(name)).getAllByRole('cell')[3].textContent;

beforeEach(() => {
  for (const fn of Object.values(mocked)) fn.mockReset();
});
afterEach(cleanup);

describe('AdminStore: produtos', () => {
  it('carrega a lista do admin, com os sem estoque e os desativados, e não a vitrine', async () => {
    await renderPage();
    expect(mocked.get).toHaveBeenCalledWith('/products/admin/all');
    expect(mocked.get).not.toHaveBeenCalledWith('/products');
    const names = within(screen.getByRole('table', { name: 'Produtos' }))
      .getAllByRole('row')
      .slice(1)
      .map((r) => r.getAttribute('aria-label'));
    expect(names).toEqual(['Óleo de barba', 'Pente', 'Pomada', 'Shampoo']);
    expect(within(row('Pente')).getByText('Desativado')).toBeTruthy();
  });

  it('avisa o estoque baixo dos ativos na linha e no resumo', async () => {
    await renderPage();
    expect(stock('Óleo de barba')).toBe('0 unSem estoque');
    expect(stock('Pomada')).toBe('3 unEstoque baixo');
    expect(stock('Pente')).toBe('0 un');
    expect(stock('Shampoo')).toBe('20 un');
    expect(screen.getByRole('note').textContent).toBe('2 produtos com estoque baixo ou zerado: Óleo de barba, Pomada.');
  });

  it('sem produto com estoque baixo, não há resumo', async () => {
    serve([PENTE, SHAMPOO]);
    render(<AdminStore />);
    await screen.findByRole('row', { name: 'Shampoo' });
    expect(screen.queryByRole('note')).toBeNull();
  });

  it('sem produtos, diz que não há nenhum', async () => {
    serve([]);
    render(<AdminStore />);
    expect(await screen.findByText('Nenhum produto cadastrado.')).toBeTruthy();
  });

  it('a falha na carga mostra a mensagem da API e "Tentar de novo" carrega de novo', async () => {
    mocked.get.mockRejectedValueOnce(httpError(403, 'Acesso restrito a administradores.'));
    render(<AdminStore />);
    expect((await screen.findByRole('alert')).textContent).toBe('Acesso restrito a administradores.');

    serve();
    click('Tentar de novo');
    expect(await screen.findByRole('row', { name: 'Pomada' })).toBeTruthy();
  });
});

describe('AdminStore: histórico', () => {
  it('"Histórico" mostra as movimentações do produto', async () => {
    await renderPage();
    click('Histórico', row('Pomada'));

    const section = await screen.findByRole('region', { name: 'Histórico de Pomada' });
    expect(await within(section).findByText('+3 un')).toBeTruthy();
    expect(within(section).getByText('Nota 12')).toBeTruthy();
    expect(mocked.get).toHaveBeenCalledWith('/products/pomada/inventory');

    click('Fechar histórico');
    expect(screen.queryByRole('region', { name: 'Histórico de Pomada' })).toBeNull();
  });

  it('a falha do histórico mostra a mensagem da API', async () => {
    await renderPage(undefined, httpError(404, 'Produto não encontrado.'));
    click('Histórico', row('Pomada'));
    expect((await screen.findByRole('alert')).textContent).toBe('Produto não encontrado.');
    expect(screen.getByRole('button', { name: 'Tentar de novo' })).toBeTruthy();
  });
});

describe('AdminStore: movimentação', () => {
  it('pede confirmação, manda o sinal do tipo, atualiza o estoque e recarrega o histórico aberto', async () => {
    await renderPage();
    click('Histórico', row('Pomada'));
    await screen.findByText('+3 un');
    mocked.post.mockResolvedValue({ data: { ...POMADA, stock_quantity: 1 } });
    serve(undefined, [makeMovement('m2', POMADA, { movement_type: 'loss', quantity: -2 }), ENTRADA]);

    click('Movimentar', row('Pomada'));
    type('Tipo', 'loss');
    type('Quantidade (em estoque: 3 un)', '2');
    type('Observação (opcional)', ' Vencida ');
    click('Registrar movimentação');

    expect(
      screen.getByText('Registrar saída de 2 un de Pomada (perda ou avaria)? O estoque passa de 3 para 1 un.'),
    ).toBeTruthy();
    expect(mocked.post).not.toHaveBeenCalled();
    click('Confirmar');

    expect(await screen.findByText('Movimentação registrada.')).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/products/pomada/inventory', {
      movement_type: 'loss',
      quantity: -2,
      notes: 'Vencida',
    });
    expect(stock('Pomada')).toBe('1 unEstoque baixo');
    expect(screen.queryByRole('form', { name: 'Movimentar estoque de Pomada' })).toBeNull();
    expect(await screen.findByText('-2 un')).toBeTruthy();
  });

  it('a reposição do produto sem estoque tira o aviso do resumo', async () => {
    await renderPage();
    mocked.post.mockResolvedValue({ data: { ...OLEO, stock_quantity: 12 } });
    click('Movimentar', row('Óleo de barba'));
    type('Quantidade (em estoque: 0 un)', '12');
    click('Registrar movimentação');
    click('Confirmar');

    expect(await screen.findByText('Movimentação registrada.')).toBeTruthy();
    expect(mocked.post).toHaveBeenCalledWith('/products/oleo/inventory', { movement_type: 'restock', quantity: 12, notes: null });
    expect(stock('Óleo de barba')).toBe('12 un');
    expect(screen.getByRole('note').textContent).toBe('1 produto com estoque baixo ou zerado: Pomada.');
  });

  it('a quantidade inválida e a saída maior que o estoque são recusadas sem chamada', async () => {
    await renderPage();
    click('Movimentar', row('Pomada'));
    click('Registrar movimentação');
    expect((await screen.findByRole('alert')).textContent).toBe(QUANTITY_ERROR);

    type('Tipo', 'sale');
    type('Quantidade (em estoque: 3 un)', '4');
    click('Registrar movimentação');
    expect((await screen.findByRole('alert')).textContent).toBe('Estoque insuficiente: há só 3 un.');
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it('"Voltar" não chama a API, e "Cancelar" fecha o formulário', async () => {
    await renderPage();
    click('Movimentar', row('Pomada'));
    type('Quantidade (em estoque: 3 un)', '1');
    click('Registrar movimentação');
    click('Voltar');
    click('Cancelar');
    expect(screen.queryByRole('form', { name: 'Movimentar estoque de Pomada' })).toBeNull();
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it('o produto desativado só oferece perda e ajuste', async () => {
    await renderPage();
    click('Movimentar', row('Pente'));
    const options = Array.from((screen.getByLabelText('Tipo') as HTMLSelectElement).options).map((o) => o.value);
    expect(options).toEqual(['adjustment-in', 'loss', 'adjustment-out']);
  });

  it.each([
    [
      httpError(400, 'Estoque insuficiente. Tentativa de remover 2, mas só existem 1 unidades.'),
      'Estoque insuficiente. Tentativa de remover 2, mas só existem 1 unidades.',
    ],
    [
      httpError(422, [{ msg: 'Value error, Venda e perda são saídas: a quantidade deve ser negativa.' }]),
      'Venda e perda são saídas: a quantidade deve ser negativa.',
    ],
  ])('o erro da API aparece no formulário, e o estoque continua', async (error, message) => {
    await renderPage();
    mocked.post.mockRejectedValue(error);
    click('Movimentar', row('Pomada'));
    type('Tipo', 'sale');
    type('Quantidade (em estoque: 3 un)', '2');
    click('Registrar movimentação');
    click('Confirmar');

    expect((await screen.findByRole('alert')).textContent).toBe(message);
    expect(stock('Pomada')).toBe('3 unEstoque baixo');
    expect(screen.getByRole('form', { name: 'Movimentar estoque de Pomada' })).toBeTruthy();
    expect(screen.queryByText('Movimentação registrada.')).toBeNull();
  });
});
