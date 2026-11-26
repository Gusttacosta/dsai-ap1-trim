// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ALUGUEL, LUZ, makeExpense } from '../../testUtils/expenses';
import ExpenseFilters, { ALL, NONE, filterByCategory } from './ExpenseFilters';

// SPEC/2026-11-26-painel-despesas.md: período para a API e categoria na tela.

const E1 = makeExpense('e1', {}, ALUGUEL);
const E2 = makeExpense('e2', {}, LUZ);
const E3 = makeExpense('e3');

afterEach(cleanup);

describe('filterByCategory', () => {
  it('"Todas" não filtra', () => {
    expect(filterByCategory([E1, E2, E3], ALL)).toEqual([E1, E2, E3]);
  });

  it('uma categoria deixa só as dela', () => {
    expect(filterByCategory([E1, E2, E3], 'luz')).toEqual([E2]);
  });

  it('"Sem categoria" deixa só as que não têm', () => {
    expect(filterByCategory([E1, E2, E3], NONE)).toEqual([E3]);
  });
});

describe('ExpenseFilters', () => {
  function renderFilters() {
    const handlers = { onPeriod: vi.fn(), onCategory: vi.fn() };
    render(
      <ExpenseFilters period={{ start: '2026-11-01', end: '' }} category={ALL} categories={[ALUGUEL, LUZ]} {...handlers} />,
    );
    return handlers;
  }

  it('mudar as datas avisa o período inteiro', () => {
    const { onPeriod } = renderFilters();

    fireEvent.change(screen.getByLabelText('Até'), { target: { value: '2026-11-30' } });
    expect(onPeriod).toHaveBeenLastCalledWith({ start: '2026-11-01', end: '2026-11-30' });

    fireEvent.change(screen.getByLabelText('De'), { target: { value: '' } });
    expect(onPeriod).toHaveBeenLastCalledWith({ start: '', end: '' });
  });

  it('a categoria lista "Todas", as categorias e "Sem categoria"', () => {
    const { onCategory } = renderFilters();
    const select = screen.getByLabelText('Categoria') as HTMLSelectElement;

    expect([...select.options].map((o) => o.text)).toEqual(['Todas', 'Aluguel', 'Luz', 'Sem categoria']);

    fireEvent.change(select, { target: { value: NONE } });
    expect(onCategory).toHaveBeenCalledWith(NONE);
  });
});
