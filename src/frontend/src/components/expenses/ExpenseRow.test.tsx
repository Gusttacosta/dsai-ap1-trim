// @vitest-environment jsdom
import { cleanup, fireEvent, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ALUGUEL, makeExpense } from '../../testUtils/expenses';
import { renderInTable } from '../../testUtils/renderInTable';
import { formatPrice } from '../../utils/serviceValidation';
import ExpenseRow from './ExpenseRow';

// SPEC/2026-11-26-painel-despesas.md: a linha da despesa e a exclusão com confirmação.

const RENT = makeExpense('e1', { description: 'Aluguel', amount: '1500.5', payment_date: '2026-11-05', is_recurring: true }, ALUGUEL);

function renderRow(expense = RENT, busy = false) {
  const handlers = { onEdit: vi.fn(), onDelete: vi.fn() };
  renderInTable(<ExpenseRow expense={expense} busy={busy} {...handlers} />);
  return handlers;
}

const cells = () => within(screen.getByRole('row')).getAllByRole('cell').map((c) => c.textContent);
const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));

afterEach(cleanup);

describe('ExpenseRow', () => {
  it('mostra data, descrição, categoria, valor em reais e a recorrência', () => {
    renderRow();

    expect(cells().slice(0, 5)).toEqual(['05/11/2026', 'Aluguel', 'Aluguel', formatPrice('1500.50'), 'Sim']);
    expect(formatPrice('1500.50')).toMatch(/^R\$\s1\.500,50$/);
  });

  it('sem categoria, diz isso', () => {
    renderRow(makeExpense('e2'));

    expect(cells()[2]).toBe('Sem categoria');
    expect(cells()[4]).toBe('Não');
  });

  it('"Editar" chama onEdit com a despesa', () => {
    const { onEdit } = renderRow();

    click('Editar');

    expect(onEdit).toHaveBeenCalledWith(RENT);
  });

  it('"Excluir" pede confirmação antes de chamar onDelete', () => {
    const { onDelete } = renderRow();

    click('Excluir');
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByText('Excluir esta despesa?')).toBeTruthy();

    click('Confirmar');
    expect(onDelete).toHaveBeenCalledWith(RENT);
  });

  it('"Voltar" desiste da exclusão', () => {
    const { onDelete } = renderRow();

    click('Excluir');
    click('Voltar');

    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Editar' })).toBeTruthy();
  });

  it('ocupada, os botões ficam desabilitados', () => {
    renderRow(RENT, true);

    expect(screen.getByRole('button', { name: 'Editar' })).toHaveProperty('disabled', true);
    expect(screen.getByRole('button', { name: 'Excluir' })).toHaveProperty('disabled', true);
  });
});
