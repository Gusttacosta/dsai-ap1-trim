import { useCallback } from 'react';
import api from '../api';
import { useApiResource } from './useApiResource';

// Agendamentos do cliente logado em "Minha conta": carga pelo GET /appointments/me e o
// cancelamento pelo PUT /appointments/{id}/cancel (SPEC/2026-11-25-meus-agendamentos.md).
// O cancelamento devolve o agendamento como o backend gravou e lança o erro da API, para
// quem chamou mostrar a mensagem.

export type MyAppointmentItem = {
  id: string;
  service_name: string;
  locked_price: string;
  duration_minutes: number;
};

export type MyAppointment = {
  id: string;
  barber_id: string;
  start_datetime: string;
  end_datetime: string;
  status: string;
  total_price: string;
  items: MyAppointmentItem[];
};

type PublicBarber = { id: string; full_name: string };

/** Nome de cada barbeiro da vitrine. Sem a vitrine, os agendamentos aparecem do mesmo jeito. */
async function loadBarberNames(): Promise<Record<string, string>> {
  try {
    const response = await api.get<PublicBarber[]>('/barbers');
    const barbers = Array.isArray(response.data) ? response.data : [];
    return Object.fromEntries(barbers.map((b) => [b.id, b.full_name]));
  } catch {
    return {};
  }
}

type Loaded = { appointments: MyAppointment[]; barberNames: Record<string, string> };

async function loadMine(): Promise<Loaded> {
  const [response, barberNames] = await Promise.all([api.get<MyAppointment[]>('/appointments/me'), loadBarberNames()]);
  return { appointments: Array.isArray(response.data) ? response.data : [], barberNames };
}

const EMPTY: Loaded = { appointments: [], barberNames: {} };

export function useMyAppointments() {
  const { data, setData, status, loadError, reload } = useApiResource(
    loadMine,
    EMPTY,
    'Não foi possível carregar seus agendamentos.',
  );

  /** Cancela e põe na lista o agendamento como o backend devolveu ("cancelled"). */
  const cancelAppointment = useCallback(async (id: string) => {
    const saved = (await api.put<MyAppointment>(`/appointments/${id}/cancel`)).data;
    setData((current) => ({
      ...current,
      appointments: current.appointments.map((a) => (a.id === saved.id ? saved : a)),
    }));
    return saved;
  }, [setData]);

  return { ...data, status, loadError, reload, cancelAppointment };
}
