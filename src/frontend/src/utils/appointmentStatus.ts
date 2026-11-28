// Regras de status do agendamento no painel (SPEC/2026-11-18-status-agendamento.md)
// e na conta do cliente (SPEC/2026-11-25-meus-agendamentos.md).

export interface AppointmentLike {
  status: string;
  start_datetime: string;
}

/** Status em que o agendamento ainda vai acontecer: dá para finalizar ou cancelar. */
const ACTIVE = ['pending', 'confirmed'];

export const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  confirmed: 'Confirmado',
  completed: 'Concluído',
  cancelled: 'Cancelado',
  no_show: 'Não compareceu',
};

const startsAt = (appointment: AppointmentLike) => new Date(appointment.start_datetime).getTime();

/** "Finalizar" só para agendamento pendente ou confirmado que já começou. */
export function canFinish(appointment: AppointmentLike, now: Date = new Date()): boolean {
  return (
    ACTIVE.includes(appointment.status) && startsAt(appointment) <= now.getTime()
  );
}

/** "Cancelar" (cliente) só para agendamento pendente ou confirmado que ainda não começou,
 * a mesma regra de AppointmentService.cancel_by_client no backend. */
export function canCancel(appointment: AppointmentLike, now: Date = new Date()): boolean {
  return ACTIVE.includes(appointment.status) && startsAt(appointment) > now.getTime();
}

/** Próximos (início no futuro, do mais próximo ao mais distante) e anteriores (do mais recente ao mais antigo). */
export function splitByStart<T extends AppointmentLike>(appointments: T[], now: Date = new Date()) {
  const byStart = [...appointments].sort((a, b) => startsAt(a) - startsAt(b));
  return {
    upcoming: byStart.filter((a) => startsAt(a) > now.getTime()),
    past: byStart.filter((a) => startsAt(a) <= now.getTime()).reverse(),
  };
}
