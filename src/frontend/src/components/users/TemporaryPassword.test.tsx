// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import TemporaryPassword from './TemporaryPassword';

// A senha temporária mostrada uma vez, com "Copiar" (SPEC/2026-11-25-admin-usuarios.md).

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function stubClipboard(writeText: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } });
}

describe('TemporaryPassword', () => {
  it('mostra a senha e para quem ela é', () => {
    render(<TemporaryPassword userName="Ana" password="Abc123def456" onClose={vi.fn()} />);

    expect(screen.getByRole('heading').textContent).toBe('Senha temporária de Ana');
    expect(screen.getByLabelText('Senha temporária').textContent).toBe('Abc123def456');
  });

  it('"Copiar" põe a senha na área de transferência e avisa', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubClipboard(writeText);
    render(<TemporaryPassword userName="Ana" password="Abc123def456" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Copiar' }));

    expect((await screen.findByRole('status')).textContent).toBe('Senha copiada.');
    expect(writeText).toHaveBeenCalledWith('Abc123def456');
  });

  it('se copiar falhar, pede para copiar à mão', async () => {
    stubClipboard(vi.fn().mockRejectedValue(new Error('negado')));
    render(<TemporaryPassword userName="Ana" password="Abc123def456" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Copiar' }));

    expect((await screen.findByRole('alert')).textContent).toMatch(/copie à mão/);
  });

  it('"Fechar" chama onClose', () => {
    const onClose = vi.fn();
    render(<TemporaryPassword userName="Ana" password="Abc123def456" onClose={onClose} />);

    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
