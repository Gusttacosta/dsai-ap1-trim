// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import AdminNotifications from './AdminNotifications';

// SPEC/2026-11-25-notificacoes.md (#75): o aviso geral passa a ser enviado de verdade.

vi.mock('../api', () => ({ default: { post: vi.fn() } }));
const mocked = api as unknown as { post: ReturnType<typeof vi.fn> };

function fill(title: string, message: string) {
  fireEvent.change(screen.getByLabelText('Título'), { target: { value: title } });
  fireEvent.change(screen.getByLabelText('Mensagem'), { target: { value: message } });
}

beforeEach(() => {
  mocked.post.mockReset();
});
afterEach(cleanup);

describe('AdminNotifications', () => {
  it('envia o aviso para o público escolhido e mostra quantos receberam', async () => {
    mocked.post.mockResolvedValue({ data: { detail: 'Mensagem enviada para 12 usuários.' } });
    render(<AdminNotifications />);

    fireEvent.change(screen.getByLabelText('Público'), { target: { value: 'clients' } });
    fill('  Feriado ', ' Fechados na sexta. ');
    fireEvent.click(screen.getByRole('button', { name: 'Enviar aviso' }));

    expect((await screen.findByRole('status')).textContent).toBe('Mensagem enviada para 12 usuários.');
    expect(mocked.post).toHaveBeenCalledWith('/notifications/broadcast', {
      title: 'Feriado',
      message: 'Fechados na sexta.',
      audience: 'clients',
    });
    expect((screen.getByLabelText('Título') as HTMLInputElement).value).toBe('');
  });

  it('não envia sem título ou mensagem', () => {
    render(<AdminNotifications />);
    fill('   ', 'Mensagem');
    const button = screen.getByRole('button', { name: 'Enviar aviso' }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    fireEvent.click(button);
    expect(mocked.post).not.toHaveBeenCalled();
  });

  it('mostra o erro do servidor e mantém o texto', async () => {
    const config = { headers: {} } as InternalAxiosRequestConfig;
    const response = { status: 422, data: { detail: 'Título inválido.' }, statusText: '', headers: {}, config } as AxiosResponse;
    mocked.post.mockRejectedValue(new AxiosError('HTTP 422', AxiosError.ERR_BAD_REQUEST, config, null, response));
    render(<AdminNotifications />);

    fill('Feriado', 'Fechados.');
    fireEvent.click(screen.getByRole('button', { name: 'Enviar aviso' }));

    expect((await screen.findByRole('alert')).textContent).toBe('Título inválido.');
    await waitFor(() => expect((screen.getByLabelText('Título') as HTMLInputElement).value).toBe('Feriado'));
  });
});
