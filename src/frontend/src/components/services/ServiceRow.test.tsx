// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AdminService } from '../../hooks/useAdminServices';
import ServiceRow from './ServiceRow';

// SPEC/2026-11-23-painel-servicos.md: a linha mostra a situação e pede confirmação para desativar.

const CORTE: AdminService = {
  id: 'c1',
  name: 'Corte',
  description: 'Tesoura e máquina',
  price: '35.5',
  duration_minutes: 30,
  is_active: true,
};

function renderRow(service: AdminService = CORTE, busy = false) {
  const handlers = { onEdit: vi.fn(), onDeactivate: vi.fn(), onReactivate: vi.fn() };
  render(
    <table>
      <tbody>
        <ServiceRow service={service} busy={busy} {...handlers} />
      </tbody>
    </table>,
  );
  return handlers;
}

const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));

afterEach(cleanup);

describe('ServiceRow', () => {
  it('mostra nome, descrição, duração, preço em reais e a situação', () => {
    renderRow();

    const row = screen.getByRole('row', { name: 'Corte' });
    expect(row.textContent).toContain('Tesoura e máquina');
    expect(row.textContent).toContain('30 min');
    expect(row.textContent?.replace(/\s/g, ' ')).toContain('R$ 35,50');
    expect(screen.getByText('Ativo')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Desativar' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Reativar' })).toBeNull();
  });

  it('serviço desativado mostra "Desativado" e o botão Reativar', () => {
    renderRow({ ...CORTE, is_active: false, description: null });

    expect(screen.getByText('Desativado')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Reativar' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Desativar' })).toBeNull();
  });

  it('Editar entrega o serviço', () => {
    const { onEdit } = renderRow();

    click('Editar');

    expect(onEdit).toHaveBeenCalledWith(CORTE);
  });

  it('Desativar só pede confirmação, sem chamar a ação', () => {
    const { onDeactivate } = renderRow();

    click('Desativar');

    expect(screen.getByText('Desativar este serviço?')).toBeTruthy();
    expect(onDeactivate).not.toHaveBeenCalled();
  });

  it('Confirmar chama a desativação uma vez e fecha a confirmação', () => {
    const { onDeactivate } = renderRow();

    click('Desativar');
    click('Confirmar');

    expect(onDeactivate).toHaveBeenCalledTimes(1);
    expect(onDeactivate).toHaveBeenCalledWith(CORTE);
    expect(screen.queryByText('Desativar este serviço?')).toBeNull();
  });

  it('Voltar fecha a confirmação sem desativar', () => {
    const { onDeactivate } = renderRow();

    click('Desativar');
    click('Voltar');

    expect(onDeactivate).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Desativar' })).toBeTruthy();
  });

  it('Reativar chama a ação direto, sem confirmação', () => {
    const inactive = { ...CORTE, is_active: false };
    const { onReactivate } = renderRow(inactive);

    click('Reativar');

    expect(onReactivate).toHaveBeenCalledWith(inactive);
  });

  it('com uma ação em andamento, os botões ficam desabilitados', () => {
    renderRow(CORTE, true);

    expect(screen.getByRole('button', { name: 'Editar' })).toHaveProperty('disabled', true);
    expect(screen.getByRole('button', { name: 'Desativar' })).toHaveProperty('disabled', true);
  });
});
