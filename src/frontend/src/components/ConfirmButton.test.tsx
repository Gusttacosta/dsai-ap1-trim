// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ConfirmButton from './ConfirmButton';

// Confirmação no próprio lugar (SPEC/2026-11-23-painel-servicos.md e SPEC/2026-11-25-meus-agendamentos.md).

function renderButton(busy = false) {
  const onConfirm = vi.fn();
  render(
    <ConfirmButton label="Cancelar" ariaLabel="Cancelar o corte" question="Cancelar este agendamento?" onConfirm={onConfirm} busy={busy}>
      <button type="button">Outra ação</button>
    </ConfirmButton>,
  );
  return onConfirm;
}

const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));

afterEach(cleanup);

describe('ConfirmButton', () => {
  it('mostra o botão com o nome acessível e as outras ações', () => {
    renderButton();

    expect(screen.getByRole('button', { name: 'Cancelar o corte' }).textContent).toBe('Cancelar');
    expect(screen.getByRole('button', { name: 'Outra ação' })).toBeTruthy();
    expect(screen.queryByText('Cancelar este agendamento?')).toBeNull();
  });

  it('o botão só pede confirmação e esconde as outras ações', () => {
    const onConfirm = renderButton();

    click('Cancelar o corte');

    expect(screen.getByText('Cancelar este agendamento?')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Outra ação' })).toBeNull();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('Confirmar chama a ação uma vez e fecha a confirmação', () => {
    const onConfirm = renderButton();

    click('Cancelar o corte');
    click('Confirmar');

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('Cancelar este agendamento?')).toBeNull();
  });

  it('Voltar fecha a confirmação sem chamar a ação', () => {
    const onConfirm = renderButton();

    click('Cancelar o corte');
    click('Voltar');

    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Cancelar o corte' })).toBeTruthy();
  });

  it('com uma ação em andamento, o botão fica desabilitado', () => {
    renderButton(true);

    expect(screen.getByRole('button', { name: 'Cancelar o corte' })).toHaveProperty('disabled', true);
  });
});
