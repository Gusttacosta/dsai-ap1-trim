// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { MyAppointment } from '../../hooks/useMyAppointments';
import AppointmentItem from './AppointmentItem';

// SPEC/2026-11-25-meus-agendamentos.md: um agendamento com data no fuso da barbearia, status,
// serviços, barbeiro e "Cancelar" só quando a regra do backend deixa.

const NOW = new Date('2026-12-01T15:00:00Z'); // 12:00 em Brasília

const APPOINTMENT: MyAppointment = {
  id: 'a1',
  barber_id: 'b1',
  start_datetime: '2026-12-02T13:00:00Z', // 10:00 em Brasília
  end_datetime: '2026-12-02T13:50:00Z',
  status: 'confirmed',
  total_price: '65.00',
  items: [
    { id: 'i1', service_name: 'Corte', locked_price: '40.00', duration_minutes: 30 },
    { id: 'i2', service_name: 'Barba', locked_price: '25.00', duration_minutes: 20 },
  ],
};

function renderItem(extra: Partial<MyAppointment> = {}, busy = false) {
  const onCancel = vi.fn();
  render(
    <ul>
      <AppointmentItem appointment={{ ...APPOINTMENT, ...extra }} barberName="João" busy={busy} onCancel={onCancel} />
    </ul>,
  );
  return onCancel;
}

const cancelButton = () => screen.queryByRole('button', { name: /^Cancelar o agendamento/ });

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(NOW);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe('AppointmentItem', () => {
  it('mostra data e hora no fuso da barbearia, status, serviços, barbeiro e total', () => {
    renderItem();

    const item = screen.getByRole('listitem', { name: 'qua., 02/12/2026 às 10:00, Corte + Barba' });
    expect(within(item).getByText('Confirmado')).toBeTruthy();
    expect(item.textContent?.replace(/\s/g, ' ')).toContain('Corte + Barba · com João · R$ 65,00');
  });

  it.each(['pending', 'confirmed'])('%s no futuro: mostra "Cancelar"', (status) => {
    renderItem({ status });

    expect(cancelButton()?.textContent).toBe('Cancelar');
    expect(cancelButton()?.getAttribute('aria-label')).toBe('Cancelar o agendamento de qua., 02/12/2026 às 10:00');
  });

  it.each([
    ['completed', 'Concluído'],
    ['cancelled', 'Cancelado'],
    ['no_show', 'Não compareceu'],
  ])('%s: mostra "%s" e não deixa cancelar', (status, label) => {
    renderItem({ status });

    expect(screen.getByText(label)).toBeTruthy();
    expect(cancelButton()).toBeNull();
  });

  it('confirmado que já começou não deixa cancelar', () => {
    renderItem({ start_datetime: '2026-12-01T15:00:00Z' });

    expect(cancelButton()).toBeNull();
  });

  it('Cancelar pede confirmação e só Confirmar entrega o agendamento', () => {
    const onCancel = renderItem();

    fireEvent.click(cancelButton()!);
    expect(screen.getByText('Cancelar este agendamento?')).toBeTruthy();
    expect(onCancel).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));
    expect(onCancel).toHaveBeenCalledWith(expect.objectContaining({ id: 'a1' }));
  });

  it('com um cancelamento em andamento, o botão fica desabilitado', () => {
    renderItem({}, true);

    expect(cancelButton()).toHaveProperty('disabled', true);
  });
});
