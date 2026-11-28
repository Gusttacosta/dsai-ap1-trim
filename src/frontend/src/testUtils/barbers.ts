import type { AdminBarber } from '../hooks/useAdminBarbers';
import type { WorkDay } from '../hooks/useBarberSchedule';

// Dados de barbeiros e da escala para os testes do painel (SPEC/2026-11-26-painel-barbeiros.md).

export const barber = (id: string, full_name: string, extra: Partial<AdminBarber> = {}): AdminBarber => ({
  id,
  user_id: `u-${id}`,
  full_name,
  email: `${id}@teste.com`,
  avatar_url: null,
  bio: null,
  instagram_url: null,
  commission_rate: '50.00',
  is_active: true,
  user_is_active: true,
  ...extra,
});

/** A escala padrão do backend: 9h às 18h com almoço das 12h às 13h, folga no domingo. */
export const defaultWeek = (): WorkDay[] =>
  Array.from({ length: 7 }, (_, day) => ({
    id: `d${day}`,
    day_of_week: day,
    start_time: '09:00:00',
    end_time: '18:00:00',
    break_start: day === 0 ? null : '12:00:00',
    break_end: day === 0 ? null : '13:00:00',
    is_working: day !== 0,
  }));
