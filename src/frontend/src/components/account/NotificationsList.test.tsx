// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../../api';
import NotificationsList from './NotificationsList';

// SPEC/2026-11-25-notificacoes.md (#75): a conta mostra as notificações, marca como lidas e apaga.

vi.mock('../../api', () => ({ default: { get: vi.fn(), put: vi.fn(), delete: vi.fn() } }));
const mocked = api as unknown as Record<'get' | 'put' | 'delete', ReturnType<typeof vi.fn>>;

const unread = { id: 'n1', title: 'Agendamento confirmado', message: 'Seu horário de 02/12 às 10:00 foi confirmado.', type: 'appointment_reminder', is_read: false, created_at: '2026-12-01T11:00:00Z' };
const read = { id: 'n2', title: 'Feriado', message: 'Fechados na sexta.', type: 'system_alert', is_read: true, created_at: '2026-11-30T11:00:00Z' };

beforeEach(() => {
  mocked.get.mockReset();
  mocked.put.mockReset().mockResolvedValue({ data: {} });
  mocked.delete.mockReset().mockResolvedValue({ data: {} });
});

afterEach(cleanup);

describe('NotificationsList', () => {
  it('lista as notificações e conta as não lidas', async () => {
    mocked.get.mockResolvedValue({ data: [unread, read] });
    render(<NotificationsList />);

    expect(await screen.findByText('Seu horário de 02/12 às 10:00 foi confirmado.')).toBeTruthy();
    expect(screen.getAllByTestId('notificacao')).toHaveLength(2);
    expect(screen.getByRole('heading', { name: 'Notificações (1 não lida)' })).toBeTruthy();
    expect(mocked.get).toHaveBeenCalledWith('/notifications');
  });

  it('marca uma como lida e recarrega', async () => {
    mocked.get.mockResolvedValueOnce({ data: [unread] }).mockResolvedValueOnce({ data: [{ ...unread, is_read: true }] });
    render(<NotificationsList />);

    fireEvent.click(await screen.findByText('Marcar como lida'));

    await waitFor(() => expect(mocked.put).toHaveBeenCalledWith('/notifications/n1/read'));
    await waitFor(() => expect(screen.queryByText('Marcar como lida')).toBeNull());
  });

  it('marca todas como lidas', async () => {
    mocked.get.mockResolvedValue({ data: [unread] });
    render(<NotificationsList />);

    fireEvent.click(await screen.findByText('Marcar todas como lidas'));

    await waitFor(() => expect(mocked.put).toHaveBeenCalledWith('/notifications/read-all'));
  });

  it('apaga uma notificação', async () => {
    mocked.get.mockResolvedValueOnce({ data: [unread, read] }).mockResolvedValueOnce({ data: [unread] });
    render(<NotificationsList />);

    fireEvent.click(await screen.findByLabelText('Apagar Feriado'));

    await waitFor(() => expect(mocked.delete).toHaveBeenCalledWith('/notifications/n2'));
    await waitFor(() => expect(screen.getAllByTestId('notificacao')).toHaveLength(1));
  });

  it('mostra a lista vazia', async () => {
    mocked.get.mockResolvedValue({ data: [] });
    render(<NotificationsList />);
    expect(await screen.findByText('Nenhuma notificação por aqui.')).toBeTruthy();
  });

  it('mostra o erro do servidor', async () => {
    mocked.get.mockRejectedValue(new Error('falhou'));
    render(<NotificationsList />);
    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível carregar as notificações.');
  });
});
