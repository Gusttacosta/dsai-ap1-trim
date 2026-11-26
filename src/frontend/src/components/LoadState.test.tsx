// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import LoadState, { ActionFeedback } from './LoadState';

// Estado da carga e resultado das ações dos painéis (SPEC/2026-11-25-admin-usuarios.md).

afterEach(cleanup);

const renderState = (status: 'loading' | 'ready' | 'error', reload = vi.fn()) =>
  render(
    <LoadState status={status} loadError="Falhou." reload={reload} loadingText="Carregando...">
      <p>conteúdo</p>
    </LoadState>,
  );

describe('LoadState', () => {
  it('enquanto carrega, mostra o texto e não o conteúdo', () => {
    renderState('loading');
    expect(screen.getByText('Carregando...')).toBeTruthy();
    expect(screen.queryByText('conteúdo')).toBeNull();
  });

  it('com erro, mostra a mensagem e "Tentar de novo" chama reload', () => {
    const reload = vi.fn();
    renderState('error', reload);

    expect(screen.getByRole('alert').textContent).toBe('Falhou.');
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));
    expect(reload).toHaveBeenCalledOnce();
    expect(screen.queryByText('conteúdo')).toBeNull();
  });

  it('pronto, mostra o conteúdo', () => {
    renderState('ready');
    expect(screen.getByText('conteúdo')).toBeTruthy();
  });
});

describe('ActionFeedback', () => {
  it('mostra a mensagem e o erro só quando existem', () => {
    const { rerender } = render(<ActionFeedback message="" error="" />);
    expect(screen.queryByRole('status')).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();

    rerender(<ActionFeedback message="Feito." error="Recusado." />);
    expect(screen.getByRole('status').textContent).toBe('Feito.');
    expect(screen.getByRole('alert').textContent).toBe('Recusado.');
  });
});
