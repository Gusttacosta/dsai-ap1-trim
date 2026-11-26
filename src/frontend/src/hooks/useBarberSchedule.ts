import { useCallback } from 'react';
import api from '../api';
import { useApiResource } from './useApiResource';

// Escala da semana de um barbeiro no painel do admin: carga (GET /barbers/{id}/schedule) e a
// gravação dos 7 dias de uma vez (PUT /barbers/{id}/schedule). SPEC/2026-11-26-painel-barbeiros.md.

export type WorkDay = {
  id: string;
  day_of_week: number;
  /** "09:00:00", como o backend serializa o time. */
  start_time: string;
  end_time: string;
  break_start: string | null;
  break_end: string | null;
  is_working: boolean;
};

/** Um dia como a API recebe: horários "HH:MM", almoço null quando não há. */
export type WorkDayInput = Omit<WorkDay, 'id'>;

export function useBarberSchedule(barberId: string) {
  const load = useCallback(
    async () => (await api.get<WorkDay[]>(`/barbers/${barberId}/schedule`)).data,
    [barberId],
  );
  const { data: week, setData, status, loadError, reload } = useApiResource(
    load,
    [] as WorkDay[],
    'Não foi possível carregar a escala.',
  );

  /** Grava a semana inteira e passa a mostrar o que o backend gravou. */
  const saveWeek = useCallback(
    async (days: WorkDayInput[]) => {
      const { data } = await api.put<WorkDay[]>(`/barbers/${barberId}/schedule`, days);
      setData(data);
      return data;
    },
    [barberId],
  );

  return { week, status, loadError, reload, saveWeek };
}
