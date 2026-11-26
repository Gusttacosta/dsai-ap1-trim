// @vitest-environment jsdom
import { cleanup, fireEvent, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { barber } from '../../testUtils/barbers';
import { renderInTable } from '../../testUtils/renderInTable';
import BarberRow, { formatCommission } from './BarberRow';

// SPEC/2026-11-26-painel-barbeiros.md: uma linha da tabela de barbeiros.

afterEach(cleanup);

function renderRow(extra: Parameters<typeof barber>[2] = {}, busy = false) {
  const handlers = { onEdit: vi.fn(), onSchedule: vi.fn(), onSetActive: vi.fn() };
  const ana = barber('ana', 'Ana', extra);
  renderInTable(<BarberRow barber={ana} busy={busy} {...handlers} />);
  return { ana, ...handlers };
}

const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));

describe('BarberRow', () => {
  it('mostra nome, e-mail, comissão e situação', () => {
    renderRow({ commission_rate: '12.50' });
    expect(screen.getByText('Ana')).toBeTruthy();
    expect(screen.getByText('ana@teste.com')).toBeTruthy();
    expect(screen.getByText('12,50%')).toBeTruthy();
    expect(screen.getByText('Ativo')).toBeTruthy();
    expect(screen.queryByText('Conta desativada')).toBeNull();
  });

  it('avisa quando a conta do usuário está desativada', () => {
    renderRow({ user_is_active: false });
    expect(screen.getByText('Conta desativada')).toBeTruthy();
  });

  it('"Editar" e "Escala" chamam a ação com o barbeiro', () => {
    const { ana, onEdit, onSchedule } = renderRow();
    click('Editar');
    click('Escala');
    expect(onEdit).toHaveBeenCalledWith(ana);
    expect(onSchedule).toHaveBeenCalledWith(ana);
  });

  it('"Desativar" pede confirmação antes', () => {
    const { ana, onSetActive } = renderRow();
    click('Desativar');
    expect(onSetActive).not.toHaveBeenCalled();
    expect(screen.getByText('Desativar este barbeiro?')).toBeTruthy();

    click('Confirmar');
    expect(onSetActive).toHaveBeenCalledWith(ana, false);
  });

  it('o desativado tem "Reativar", sem confirmação', () => {
    const { ana, onSetActive } = renderRow({ is_active: false });
    expect(screen.getByText('Desativado')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Desativar' })).toBeNull();

    click('Reativar');
    expect(onSetActive).toHaveBeenCalledWith(ana, true);
  });

  it('ocupada, os botões ficam desabilitados', () => {
    renderRow({}, true);
    for (const button of screen.getAllByRole('button')) expect(button).toHaveProperty('disabled', true);
  });

  it('formata a comissão com vírgula', () => {
    expect(formatCommission('50.00')).toBe('50,00%');
    expect(formatCommission('7.5')).toBe('7,50%');
  });
});
