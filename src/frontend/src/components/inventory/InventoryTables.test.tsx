// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../../api';
import { httpError } from '../../testUtils/httpError';
import { OLEO, PENTE, POMADA, SHAMPOO, makeMovement } from '../../testUtils/inventory';
import { renderInTable } from '../../testUtils/renderInTable';
import { formatPrice } from '../../utils/serviceValidation';
import InventoryHistory from './InventoryHistory';
import ProductStockRow from './ProductStockRow';

// SPEC/2026-11-26-painel-estoque.md: a linha do produto com o aviso de estoque e o histórico.

vi.mock('../../api', () => ({ default: { get: vi.fn() } }));
const mockedGet = api.get as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => mockedGet.mockReset());
afterEach(cleanup);

const cells = (name: string) => within(screen.getByRole('row', { name })).getAllByRole('cell').map((c) => c.textContent);

describe('ProductStockRow', () => {
  it('mostra o nome com o SKU, a situação, o preço e o estoque com o aviso', () => {
    renderInTable(<ProductStockRow product={POMADA} busy={false} onHistory={vi.fn()} onMove={vi.fn()} />);
    expect(cells('Pomada').slice(0, 4)).toEqual(['PomadaSKU PO-01', 'Ativo', formatPrice('45.00'), '3 unEstoque baixo']);
  });

  it.each([
    [OLEO, '0 unSem estoque'],
    [SHAMPOO, '20 un'],
    [PENTE, '0 un'],
  ])('o aviso de %s', (product, stock) => {
    renderInTable(<ProductStockRow product={product} busy={false} onHistory={vi.fn()} onMove={vi.fn()} />);
    expect(cells(product.name)[3]).toBe(stock);
  });

  it('o desativado mostra a situação', () => {
    renderInTable(<ProductStockRow product={PENTE} busy={false} onHistory={vi.fn()} onMove={vi.fn()} />);
    expect(cells('Pente')[1]).toBe('Desativado');
  });

  it('"Histórico" e "Movimentar" chamam com o produto; com um formulário aberto, "Movimentar" fica desabilitado', () => {
    const onHistory = vi.fn();
    const onMove = vi.fn();
    const { rerender } = renderInTable(<ProductStockRow product={POMADA} busy={false} onHistory={onHistory} onMove={onMove} />);
    fireEvent.click(screen.getByRole('button', { name: 'Histórico' }));
    fireEvent.click(screen.getByRole('button', { name: 'Movimentar' }));
    expect(onHistory).toHaveBeenCalledWith(POMADA);
    expect(onMove).toHaveBeenCalledWith(POMADA);

    rerender(
      <table>
        <tbody>
          <ProductStockRow product={POMADA} busy onHistory={onHistory} onMove={onMove} />
        </tbody>
      </table>,
    );
    expect(screen.getByRole('button', { name: 'Movimentar' })).toHaveProperty('disabled', true);
  });
});

describe('InventoryHistory', () => {
  it('mostra a data no fuso da barbearia, o tipo, a quantidade com sinal e a observação', async () => {
    mockedGet.mockResolvedValue({
      data: [
        makeMovement('m2', POMADA, { movement_type: 'loss', quantity: -2, notes: 'Caiu no chão', created_at: '2026-11-26T17:30:00Z' }),
        makeMovement('m1', POMADA, { movement_type: 'restock', quantity: 5, created_at: '2026-11-25T13:00:00Z' }),
      ],
    });
    render(<InventoryHistory product={POMADA} onClose={vi.fn()} />);

    const table = await screen.findByRole('table', { name: 'Movimentações' });
    expect(mockedGet).toHaveBeenCalledWith('/products/pomada/inventory');
    const rows = within(table).getAllByRole('row').slice(1).map((r) => within(r).getAllByRole('cell').map((c) => c.textContent));
    expect(rows).toEqual([
      ['qui., 26/11/2026 às 14:30', 'Perda', '-2 un', 'Caiu no chão'],
      ['qua., 25/11/2026 às 10:00', 'Reposição', '+5 un', '—'],
    ]);
    expect(screen.getByRole('heading', { name: 'Histórico de Pomada' })).toBeTruthy();
  });

  it('vazio, diz que não há movimentações; "Fechar histórico" fecha', async () => {
    mockedGet.mockResolvedValue({ data: [] });
    const onClose = vi.fn();
    render(<InventoryHistory product={POMADA} onClose={onClose} />);
    expect(await screen.findByText('Nenhuma movimentação ainda.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Fechar histórico' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('a falha mostra a mensagem da API e "Tentar de novo" carrega de novo', async () => {
    mockedGet.mockRejectedValueOnce(httpError(404, 'Produto não encontrado.'));
    mockedGet.mockResolvedValueOnce({ data: [] });
    render(<InventoryHistory product={POMADA} onClose={vi.fn()} />);
    expect((await screen.findByRole('alert')).textContent).toBe('Produto não encontrado.');

    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));
    expect(await screen.findByText('Nenhuma movimentação ainda.')).toBeTruthy();
  });
});
