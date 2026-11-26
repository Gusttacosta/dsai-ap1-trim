// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../../api';
import { defaultWeek } from '../../testUtils/barbers';
import { httpError } from '../../testUtils/httpError';
import { BREAK_OUTSIDE, END_BEFORE_START, INCOMPLETE_BREAK } from '../../utils/barberValidation';
import BarberSchedule, { dayInput, weekFields } from './BarberSchedule';

// SPEC/2026-11-26-painel-barbeiros.md: a escala da semana, com almoço, gravada de uma vez.

vi.mock('../../api', () => ({ default: { get: vi.fn(), put: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; put: Mock };

function renderSchedule() {
  const handlers = { onSaved: vi.fn(), onCancel: vi.fn() };
  render(<BarberSchedule barberId="ana" barberName="Ana" {...handlers} />);
  return handlers;
}

async function loaded() {
  mocked.get.mockResolvedValue({ data: defaultWeek() });
  const handlers = renderSchedule();
  await screen.findByRole('form', { name: 'Escala de Ana' });
  return handlers;
}

const type = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Salvar escala' }));

beforeEach(() => {
  mocked.get.mockReset();
  mocked.put.mockReset();
});
afterEach(cleanup);

describe('BarberSchedule', () => {
  it('mostra os 7 dias, de domingo a sábado, com folga desabilitada', async () => {
    await loaded();
    expect(mocked.get).toHaveBeenCalledWith('/barbers/ana/schedule');
    expect(screen.getAllByRole('row', { name: /^(Domingo|Segunda|Terça|Quarta|Quinta|Sexta|Sábado)$/ })).toHaveLength(7);
    expect(screen.getByLabelText('Segunda: início')).toHaveProperty('value', '09:00');
    expect(screen.getByLabelText('Segunda: fim do almoço')).toHaveProperty('value', '13:00');
    expect(screen.getByLabelText('Domingo: trabalha')).toHaveProperty('checked', false);
    expect(screen.getByLabelText('Domingo: início')).toHaveProperty('disabled', true);
  });

  it('grava a semana inteira, com o almoço vazio como null', async () => {
    const { onSaved } = await loaded();
    fireEvent.click(screen.getByLabelText('Domingo: trabalha'));
    type('Domingo: fim', '13:00');
    type('Sábado: início do almoço', '');
    type('Sábado: fim do almoço', '');
    mocked.put.mockResolvedValue({ data: defaultWeek() });
    submit();

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    const [url, days] = mocked.put.mock.lastCall!;
    expect(url).toBe('/barbers/ana/schedule');
    expect(days).toHaveLength(7);
    expect(days[0]).toEqual({ day_of_week: 0, is_working: true, start_time: '09:00', end_time: '13:00', break_start: null, break_end: null });
    expect(days[6]).toMatchObject({ day_of_week: 6, break_start: null, break_end: null });
    expect(days[1]).toMatchObject({ break_start: '12:00', break_end: '13:00' });
  });

  it.each([
    ['Terça: fim do almoço', '', `Terça: ${INCOMPLETE_BREAK}`],
    ['Quarta: fim', '08:00', `Quarta: ${END_BEFORE_START}`],
    ['Sexta: início do almoço', '08:00', `Sexta: ${BREAK_OUTSIDE}`],
  ])('%s = "%s" é recusado na tela, sem chamar a API', async (label, value, message) => {
    await loaded();
    type(label, value);
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe(message);
    expect(mocked.put).not.toHaveBeenCalled();
  });

  it('sem mudança, diz "Nada mudou."', async () => {
    await loaded();
    submit();
    expect((await screen.findByRole('status')).textContent).toBe('Nada mudou.');
    expect(mocked.put).not.toHaveBeenCalled();
  });

  it('erro da gravação mostra a mensagem da API e não fecha', async () => {
    const { onSaved } = await loaded();
    type('Segunda: fim', '17:00');
    mocked.put.mockRejectedValue(httpError(403, 'Acesso restrito a administradores.'));
    submit();
    expect((await screen.findByRole('alert')).textContent).toBe('Acesso restrito a administradores.');
    expect(onSaved).not.toHaveBeenCalled();
  });

  it('erro da carga mostra a mensagem e "Tentar de novo"', async () => {
    mocked.get.mockRejectedValueOnce(httpError(404, 'Escala não encontrada.')).mockResolvedValueOnce({ data: defaultWeek() });
    renderSchedule();
    expect((await screen.findByRole('alert')).textContent).toBe('Escala não encontrada.');
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }));
    expect(await screen.findByRole('form', { name: 'Escala de Ana' })).toBeTruthy();
  });

  it('"Cancelar" fecha', async () => {
    const { onCancel } = await loaded();
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onCancel).toHaveBeenCalled();
  });
});

describe('conversão da escala', () => {
  it('dia faltando entra como folga, e o almoço vazio vai como null', () => {
    const fields = weekFields(defaultWeek().filter((d) => d.day_of_week !== 3));
    expect(fields).toHaveLength(7);
    expect(fields[3]).toMatchObject({ day_of_week: 3, is_working: false, break_start: '' });
    expect(dayInput(fields[3])).toMatchObject({ break_start: null, break_end: null });
  });
});
