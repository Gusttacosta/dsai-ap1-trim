// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import CatalogRow from './CatalogRow';

// SPEC/2026-11-26-painel-fidelidade.md: a linha comum dos planos e dos prêmios.

afterEach(cleanup);

function renderRow(busy = false, description: string | null = 'Corte simples') {
  const handlers = { onEdit: vi.fn(), onConfirm: vi.fn() };
  render(
    <table>
      <tbody>
        <CatalogRow name="Corte grátis" description={description} actionLabel="Desativar" question="Desativar?" busy={busy} {...handlers}>
          <td>300 pts</td>
        </CatalogRow>
      </tbody>
    </table>,
  );
  return { ...handlers, row: screen.getByRole('row', { name: 'Corte grátis' }) };
}

describe('CatalogRow', () => {
  it('mostra o nome, a descrição e as colunas de quem usa', () => {
    const { row } = renderRow();
    expect(within(row).getByText('Corte simples')).toBeTruthy();
    expect(within(row).getByText('300 pts')).toBeTruthy();
  });

  it('sem descrição, só o nome', () => {
    const { row } = renderRow(false, null);
    expect(within(row).getAllByRole('cell')[0].textContent).toBe('Corte grátis');
  });

  it('"Editar" chama onEdit; a ação só roda depois de confirmada', () => {
    const { row, onEdit, onConfirm } = renderRow();
    fireEvent.click(within(row).getByRole('button', { name: 'Editar' }));
    expect(onEdit).toHaveBeenCalled();

    fireEvent.click(within(row).getByRole('button', { name: 'Desativar' }));
    expect(within(row).getByText('Desativar?')).toBeTruthy();
    expect(onConfirm).not.toHaveBeenCalled();
    fireEvent.click(within(row).getByRole('button', { name: 'Confirmar' }));
    expect(onConfirm).toHaveBeenCalled();
  });

  it('ocupada, os botões ficam desabilitados', () => {
    const { row } = renderRow(true);
    expect(within(row).getByRole('button', { name: 'Editar' })).toHaveProperty('disabled', true);
    expect(within(row).getByRole('button', { name: 'Desativar' })).toHaveProperty('disabled', true);
  });
});
