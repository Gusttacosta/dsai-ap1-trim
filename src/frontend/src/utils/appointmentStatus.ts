// Regras de status do agendamento no painel (SPEC/2026-11-18-status-agendamento.md).

export interface AppointmentLike {
  status: string;
  start_datetime: string;
}

const FINISHABLE = ['pending', 'confirmed'];

/** "Finalizar" só para agendamento pendente ou confirmado que já começou. */
export function canFinish(appointment: AppointmentLike, now: Date = new Date()): boolean {
  return (
    FINISHABLE.includes(appointment.status) &&
    new Date(appointment.start_datetime).getTime() <= now.getTime()
  );
}
