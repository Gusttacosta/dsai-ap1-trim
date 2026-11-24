// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api';
import { CHARACTERS_ERROR, FIRST_AND_LAST_ERROR } from '../utils/guestName';
import Booking from './Booking';

// SPEC/2026-11-23-nome-do-visitante.md: a etapa do nome do visitante em /agendar (#22).

vi.mock('../api', () => ({ default: { get: vi.fn(), post: vi.fn() } }));
type Mock = ReturnType<typeof vi.fn>;
const mocked = api as unknown as { get: Mock; post: Mock };

const BARBER = { id: 'b1', full_name: 'Carlos Barbeiro', bio: null };
const SERVICE = { id: 's1', name: 'Corte', price: '40.00', duration_minutes: 30 };

function apiGet(url: string) {
  if (url === '/barbers') return Promise.resolve({ data: [BARBER] });
  if (url === '/services') return Promise.resolve({ data: [SERVICE] });
  if (url.startsWith('/appointments/availability')) return Promise.resolve({ data: { available_slots: ['10:00'] } });
  return Promise.reject(new Error(`GET inesperado: ${url}`));
}

function renderBooking() {
  render(
    <MemoryRouter initialEntries={['/agendar']}>
      <Routes>
        <Route path="/agendar" element={<Booking />} />
        <Route path="/" element={<p>Página inicial</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

const nameInput = () => screen.getByLabelText('Como podemos te chamar?');
const typeName = (value: string) => fireEvent.change(nameInput(), { target: { value } });
const next = () => screen.getByRole('button', { name: 'Próximo' });
const errorText = () => screen.getByRole('alert').textContent;

beforeEach(() => {
  localStorage.clear();
  mocked.get.mockReset().mockImplementation(apiGet);
  mocked.post.mockReset();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Booking: nome do visitante', () => {
  it('começa sem mensagem, com "Próximo" desabilitado', () => {
    renderBooking();

    expect(errorText()).toBe('');
    expect(next()).toHaveProperty('disabled', true);
    expect(nameInput().getAttribute('aria-invalid')).toBe('false');
  });

  it.each([
    ['sev', FIRST_AND_LAST_ERROR],
    ['Severino', FIRST_AND_LAST_ERROR],
    ['   ', FIRST_AND_LAST_ERROR],
    ['Ana 123', CHARACTERS_ERROR],
  ])('%j mostra a mensagem e mantém "Próximo" desabilitado', (value, message) => {
    renderBooking();

    typeName(value);

    expect(errorText()).toBe(message);
    expect(next()).toHaveProperty('disabled', true);
    expect(nameInput().getAttribute('aria-invalid')).toBe('true');
  });

  it('nome e sobrenome tiram a mensagem e habilitam "Próximo"', () => {
    renderBooking();

    typeName('sev');
    typeName('Severino Sobrinho');

    expect(errorText()).toBe('');
    expect(next()).toHaveProperty('disabled', false);
  });

  it('apagar o nome volta ao estado inicial, sem mensagem', () => {
    renderBooking();

    typeName('sev');
    typeName('');

    expect(errorText()).toBe('');
    expect(next()).toHaveProperty('disabled', true);
  });

  it('ao confirmar, o POST /appointments/guest leva o nome limpo', async () => {
    vi.spyOn(window, 'alert').mockImplementation(() => {});
    mocked.post.mockResolvedValue({ data: {} });
    renderBooking();

    typeName('  ana   de  souza ');
    fireEvent.click(next());
    fireEvent.click(await screen.findByText('Carlos Barbeiro'));
    fireEvent.click(next());
    fireEvent.click(await screen.findByText('Corte'));
    fireEvent.click(next());
    fireEvent.click(await screen.findByText('10:00'));
    fireEvent.click(next());
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar Agendamento' }));

    await waitFor(() => expect(mocked.post).toHaveBeenCalledTimes(1));
    const [endpoint, payload] = mocked.post.mock.calls[0];
    expect(endpoint).toBe('/appointments/guest');
    expect(payload).toMatchObject({ guest_name: 'ana de souza', barber_id: 'b1', service_ids: ['s1'] });
    expect(await screen.findByText('Página inicial')).toBeTruthy();
  });

  it('logado, a etapa do nome não aparece', async () => {
    localStorage.setItem('token', 'qualquer');
    renderBooking();

    expect(screen.queryByLabelText('Como podemos te chamar?')).toBeNull();
    expect(await screen.findByText('Carlos Barbeiro')).toBeTruthy();
  });
});
