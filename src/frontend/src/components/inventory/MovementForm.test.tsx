// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Product } from '../../hooks/useInventory';
import { httpError } from '../../testUtils/httpError';
import { PENTE, makeProduct } from '../../testUtils/inventory';
import { NOTES_ERROR, QUANTITY_ERROR } from '../../utils/inventory';
import MovementForm from './MovementForm';

// SPEC/2026-11-26-painel-estoque.md: a entrada e a saída de estoque, com o sinal pelo tipo e a
// confirmação.

afterEach(cleanup);

const POMADA = makeProduct('pomada', { name: 'Pomada', stock_quantity: 10 });
const QUANTITY = 'Quantidade (em estoque: 10 un)';

function renderForm(product: Product = POMADA, onSave: (...args: unknown[]) => Promise<unknown> = vi.fn(async () => undefined)) {
  render(<MovementForm product={product} onSave={onSave} onCancel={vi.fn()} />);
  return onSave;
}

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));

describe('MovementForm', () => {
  it('a entrada pergunta com o estoque antes e depois, e só grava no "Confirmar"', async () => {
    const onSave = renderForm();
    expect(screen.getByRole('form', { name: 'Movimentar estoque de Pomada' })).toBeTruthy();
    type(QUANTITY, ' 5 ');
    type('Observação (opcional)', '  Nota 123  ');
    click('Registrar movimentação');

    expect(
      await screen.findByText('Registrar entrada de 5 un de Pomada (reposição)? O estoque passa de 10 para 15 un.'),
    ).toBeTruthy();
    expect(onSave).not.toHaveBeenCalled();

    click('Confirmar');
    await vi.waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({ movement_type: 'restock', quantity: 5, notes: 'Nota 123' }),
    );
  });

  it.each([
    ['sale', 'sale', -3, 'venda'],
    ['loss', 'loss', -3, 'perda ou avaria'],
    ['adjustment-out', 'adjustment', -3, 'ajuste de inventário'],
    ['adjustment-in', 'adjustment', 3, 'ajuste de inventário'],
  ])('o tipo %s manda %s com o sinal certo', async (key, movementType, quantity, short) => {
    const onSave = renderForm();
    type('Tipo', key);
    type(QUANTITY, '3');
    click('Registrar movimentação');
    const side = quantity > 0 ? 'entrada' : 'saída';
    expect(await screen.findByText(`Registrar ${side} de 3 un de Pomada (${short})? O estoque passa de 10 para ${10 + quantity} un.`)).toBeTruthy();
    click('Confirmar');
    await vi.waitFor(() => expect(onSave).toHaveBeenCalledWith({ movement_type: movementType, quantity, notes: null }));
  });

  it.each([
    ['', '', QUANTITY_ERROR],
    ['0', '', QUANTITY_ERROR],
    ['1,5', '', QUANTITY_ERROR],
    ['-2', '', QUANTITY_ERROR],
    ['10001', '', QUANTITY_ERROR],
    ['2', 'x'.repeat(501), NOTES_ERROR],
  ])('recusa a quantidade %j (observação de %j), sem pergunta nem chamada', async (quantity, notes, message) => {
    const onSave = renderForm();
    type(QUANTITY, quantity);
    type('Observação (opcional)', notes);
    click('Registrar movimentação');
    expect((await screen.findByRole('alert')).textContent).toBe(message);
    expect(screen.queryByRole('button', { name: 'Confirmar' })).toBeNull();
    expect(onSave).not.toHaveBeenCalled();
  });

  it('a saída maior que o estoque é recusada na tela; a entrada não', async () => {
    const onSave = renderForm();
    type('Tipo', 'loss');
    type(QUANTITY, '11');
    click('Registrar movimentação');
    expect((await screen.findByRole('alert')).textContent).toBe('Estoque insuficiente: há só 10 un.');
    expect(onSave).not.toHaveBeenCalled();

    type('Tipo', 'restock');
    click('Registrar movimentação');
    expect(await screen.findByRole('button', { name: 'Confirmar' })).toBeTruthy();
  });

  it('"Voltar" e mudar um campo voltam ao formulário sem chamar a API', async () => {
    const onSave = renderForm();
    type(QUANTITY, '2');
    click('Registrar movimentação');
    click('Voltar');
    expect(screen.getByRole('button', { name: 'Registrar movimentação' })).toBeTruthy();

    click('Registrar movimentação');
    type(QUANTITY, '4');
    expect(screen.queryByRole('button', { name: 'Confirmar' })).toBeNull();
    expect(onSave).not.toHaveBeenCalled();
  });

  it('o produto desativado só oferece perda e ajuste', () => {
    renderForm(PENTE);
    const options = Array.from((screen.getByLabelText('Tipo') as HTMLSelectElement).options).map((o) => o.textContent);
    expect(options).toEqual(['Entrada: ajuste de inventário', 'Saída: perda ou avaria', 'Saída: ajuste de inventário']);
    expect(screen.getByText('Produto desativado: só aceita perda ou ajuste de estoque.')).toBeTruthy();
  });

  it.each([
    [httpError(400, 'Produto desativado: só aceita perda ou ajuste de estoque.'), 'Produto desativado: só aceita perda ou ajuste de estoque.'],
    [httpError(422, [{ msg: 'Value error, A quantidade não pode ser zero.' }]), 'A quantidade não pode ser zero.'],
    [httpError(500), 'Não foi possível registrar a movimentação.'],
  ])('o erro da API aparece no formulário', async (error, message) => {
    renderForm(POMADA, vi.fn(async () => Promise.reject(error)));
    type(QUANTITY, '2');
    click('Registrar movimentação');
    click('Confirmar');
    expect((await screen.findByRole('alert')).textContent).toBe(message);
  });
});
