// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { REASON_ERROR } from '../../utils/galleryValidation';
import RejectButton from './RejectButton';

// SPEC/2026-11-26-painel-galeria.md: "Recusar" pede o motivo na linha.

const onReject = vi.fn();

const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }));
const reason = () => screen.queryByLabelText('Motivo da recusa') as HTMLInputElement | null;

function renderButton() {
  render(
    <RejectButton busy={false} onReject={onReject}>
      <button>Aprovar</button>
    </RejectButton>,
  );
}

beforeEach(() => onReject.mockReset());
afterEach(cleanup);

describe('RejectButton', () => {
  it('abre o motivo no lugar das outras ações e manda o motivo aparado', async () => {
    onReject.mockResolvedValue(true);
    renderButton();

    click('Recusar');
    expect(screen.queryByRole('button', { name: 'Aprovar' })).toBeNull();
    fireEvent.change(reason()!, { target: { value: '  Foto desfocada ' } });
    click('Confirmar recusa');

    await waitFor(() => expect(reason()).toBeNull());
    expect(onReject).toHaveBeenCalledWith('Foto desfocada');
  });

  it('motivo vazio é recusado sem chamada', () => {
    renderButton();

    click('Recusar');
    fireEvent.change(reason()!, { target: { value: '   ' } });
    click('Confirmar recusa');

    expect(screen.getByRole('alert').textContent).toBe(REASON_ERROR);
    expect(onReject).not.toHaveBeenCalled();
  });

  it('a falha mantém o campo aberto com o motivo', async () => {
    onReject.mockResolvedValue(false);
    renderButton();

    click('Recusar');
    fireEvent.change(reason()!, { target: { value: 'Fora do padrão' } });
    click('Confirmar recusa');

    await waitFor(() => expect(onReject).toHaveBeenCalled());
    expect(reason()!.value).toBe('Fora do padrão');
  });

  it('"Voltar" fecha sem recusar e devolve as outras ações', () => {
    renderButton();

    click('Recusar');
    click('Voltar');

    expect(reason()).toBeNull();
    expect(screen.getByRole('button', { name: 'Aprovar' })).toBeTruthy();
    expect(onReject).not.toHaveBeenCalled();
  });
});
