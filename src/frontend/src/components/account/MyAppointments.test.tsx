// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../../api';
import type { MyAppointment } from '../../hooks/useMyAppointments';
import { httpError, networkError } from '../../testUtils/httpError';
import MyAppointments from './MyAppointments';

// SPEC/2026-11-25-meus-agendamentos.md: próximos e anteriores, e o cancelamento pela API.

vi.mock('../../api', () => ({ default: { get: vi.fn(), put: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; put: Mock };

const NOW = new Date('2026-12-01T15:00:00Z'); // 12:00 em Brasília

const appointment = (id: string, start: string, status = 'confirmed', service = 'Corte'): MyAppointment => ({
  id,
  barber_id: 'b1',
  start_datetime: start,
  end_datetime: start,
  status,
  total_price: '40.00',
  items: [{ id: `${id}-i`, service_name: service, locked_price: '40.00', duration_minutes: 30 }],
});

const NEXT_WEEK = appointment('a1', '2026-12-08T13:00:00Z', 'confirmed', 'Barba');
const TOMORROW = appointment('a2', '2026-12-02T13:00:00Z');
const LAST_WEEK = appointment('a3', '2026-11-24T13:00:00Z', 'completed');
const LAST_MONTH = appointment('a4', '2026-11-01T13:00:00Z', 'no_show');

function load(list: MyAppointment[], barbers: unknown = [{ id: 'b1', full_name: 'João' }]) {
  mocked.get.mockImplementation(async (url: string) => ({ data: url === '/barbers' ? barbers : list }));
  render(<MyAppointments />);
}

const group = (name: string) => screen.getByRole('list', { name });
const itemNames = (name: string) => within(group(name)).getAllByRole('listitem').map((li) => li.getAttribute('aria-label'));
const cancelTomorrow = () => {
  fireEvent.click(screen.getByRole('button', { name: 'Cancelar o agendamento de qua., 02/12/2026 às 10:00' }));
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));
};

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(NOW);
  mocked.get.mockReset();
  mocked.put.mockReset();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe('MyAppointments', () => {
  it('separa próximos e anteriores, na ordem certa, com o nome do barbeiro', async () => {
    load([LAST_MONTH, NEXT_WEEK, LAST_WEEK, TOMORROW]);

    expect(await screen.findByRole('heading', { name: 'Próximos' })).toBeTruthy();
    expect(itemNames('Próximos')).toEqual(['qua., 02/12/2026 às 10:00, Corte', 'ter., 08/12/2026 às 10:00, Barba']);
    expect(itemNames('Anteriores')).toEqual(['ter., 24/11/2026 às 10:00, Corte', 'dom., 01/11/2026 às 10:00, Corte']);
    expect(within(group('Anteriores')).getByText('Não compareceu')).toBeTruthy();
    expect(screen.getAllByText(/com João/)).toHaveLength(4);
    expect(mocked.get).toHaveBeenCalledWith('/appointments/me');
  });

  it('só os próximos ativos têm "Cancelar"', async () => {
    load([TOMORROW, LAST_WEEK, appointment('a5', '2026-12-10T13:00:00Z', 'cancelled')]);

    await screen.findByRole('heading', { name: 'Próximos' });
    expect(screen.getAllByRole('button', { name: /^Cancelar o agendamento/ })).toHaveLength(1);
  });

  it('listas vazias mostram um texto', async () => {
    load([]);

    expect(await screen.findByText('Nenhum agendamento marcado.')).toBeTruthy();
    expect(screen.getByText('Nenhum agendamento anterior.')).toBeTruthy();
  });

  it('barbeiro fora da vitrine aparece como "Barbeiro"', async () => {
    load([TOMORROW], []);

    expect(await screen.findByText(/com Barbeiro/)).toBeTruthy();
  });

  it('confirmar o cancelamento chama a API e mostra o agendamento cancelado, sem o botão', async () => {
    load([TOMORROW]);
    mocked.put.mockResolvedValue({ data: { ...TOMORROW, status: 'cancelled' } });
    await screen.findByRole('heading', { name: 'Próximos' });

    cancelTomorrow();

    expect(await screen.findByRole('status')).toHaveProperty('textContent', 'Agendamento cancelado.');
    expect(mocked.put).toHaveBeenCalledWith('/appointments/a2/cancel');
    expect(within(group('Próximos')).getByText('Cancelado')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /^Cancelar o agendamento/ })).toBeNull();
  });

  it('Voltar não chama a API', async () => {
    load([TOMORROW]);
    await screen.findByRole('heading', { name: 'Próximos' });

    fireEvent.click(screen.getByRole('button', { name: /^Cancelar o agendamento/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }));

    expect(mocked.put).not.toHaveBeenCalled();
  });

  it.each([
    [httpError(400, 'Não é possível cancelar um agendamento que já começou.'), 'Não é possível cancelar um agendamento que já começou.'],
    [httpError(404, 'Agendamento não encontrado.'), 'Agendamento não encontrado.'],
    [networkError(), 'Sem conexão com o servidor. Verifique a internet e tente de novo.'],
  ])('erro ao cancelar mostra a mensagem e mantém a lista (%#)', async (error, message) => {
    load([TOMORROW]);
    mocked.put.mockRejectedValue(error);
    await screen.findByRole('heading', { name: 'Próximos' });

    cancelTomorrow();

    expect(await screen.findByRole('alert')).toHaveProperty('textContent', message);
    expect(within(group('Próximos')).getByText('Confirmado')).toBeTruthy();
    expect(screen.queryByRole('status')).toBeNull();
  });

  it('erro na carga mostra a mensagem e "Tentar de novo" recarrega', async () => {
    mocked.get.mockImplementation(async (url: string) => {
      if (url === '/barbers') return { data: [] };
      throw httpError(500);
    });
    render(<MyAppointments />);

    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Não foi possível carregar seus agendamentos.');

    mocked.get.mockImplementation(async (url: string) => ({ data: url === '/barbers' ? [] : [TOMORROW] }));
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));

    expect(await screen.findByRole('heading', { name: 'Próximos' })).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
