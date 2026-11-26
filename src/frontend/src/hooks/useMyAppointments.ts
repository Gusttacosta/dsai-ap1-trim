import { useCallback, useEffect, useState } from 'react';
import api from '../api';
import { apiErrorMessage } from '../utils/apiError';

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

export type MyAppointmentsStatus = 'loading' | 'ready' | 'error';

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

export function useMyAppointments() {
  const [appointments, setAppointments] = useState<MyAppointment[]>([]);
  const [barberNames, setBarberNames] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<MyAppointmentsStatus>('loading');
  const [loadError, setLoadError] = useState('');
  // Mudar o número pede uma nova carga ("Tentar de novo").
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setStatus('loading');
    Promise.all([api.get<MyAppointment[]>('/appointments/me'), loadBarberNames()])
      .then(([response, names]) => {
        if (!active) return;
        setAppointments(Array.isArray(response.data) ? response.data : []);
        setBarberNames(names);
        setStatus('ready');
      })
      .catch((error) => {
        if (!active) return;
        setLoadError(apiErrorMessage(error, 'Não foi possível carregar seus agendamentos.'));
        setStatus('error');
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);

  /** Cancela e põe na lista o agendamento como o backend devolveu ("cancelled"). */
  const cancelAppointment = useCallback(async (id: string) => {
    const saved = (await api.put<MyAppointment>(`/appointments/${id}/cancel`)).data;
    setAppointments((current) => current.map((a) => (a.id === saved.id ? saved : a)));
    return saved;
  }, []);

  return { appointments, barberNames, status, loadError, reload, cancelAppointment };
}
