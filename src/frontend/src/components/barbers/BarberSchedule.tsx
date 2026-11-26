import { useState } from 'react';
import shared from '../../pages/AdminShared.module.css';
import AdminForm from '../AdminForm';
import LoadState from '../LoadState';
import { useBarberSchedule, type WorkDay, type WorkDayInput } from '../../hooks/useBarberSchedule';
import { DAY_NAMES, validateWeek, type DayFields } from '../../utils/barberValidation';
import styles from '../services/Services.module.css';

// Escala da semana de um barbeiro no painel: os 7 dias, com expediente e almoço, conferidos com as
// regras do backend e gravados de uma vez (SPEC/2026-11-26-painel-barbeiros.md).

type Props = {
  barberId: string;
  barberName: string;
  /** Chamado depois de gravar a semana. */
  onSaved: () => void;
  onCancel: () => void;
};

/** "09:00:00" da API como o campo de hora mostra ("09:00"); null vira ''. */
const hhmm = (time: string | null) => (time ?? '').slice(0, 5);

/** A semana da API como os campos mostram, de domingo a sábado. Dia faltando entra como folga. */
export function weekFields(week: WorkDay[]): DayFields[] {
  return DAY_NAMES.map((_, day) => {
    const stored = week.find((d) => d.day_of_week === day);
    if (!stored) {
      return { day_of_week: day, is_working: false, start_time: '09:00', end_time: '18:00', break_start: '', break_end: '' };
    }
    return {
      day_of_week: day,
      is_working: stored.is_working,
      start_time: hhmm(stored.start_time),
      end_time: hhmm(stored.end_time),
      break_start: hhmm(stored.break_start),
      break_end: hhmm(stored.break_end),
    };
  });
}

/** Um dia dos campos no formato da API: almoço vazio vira null. */
export const dayInput = (day: DayFields): WorkDayInput => ({
  ...day,
  break_start: day.break_start || null,
  break_end: day.break_end || null,
});

const TIME_FIELDS = [
  ['start_time', 'início'],
  ['end_time', 'fim'],
  ['break_start', 'início do almoço'],
  ['break_end', 'fim do almoço'],
] as const;

const WeekForm = ({ week, barberName, save, onCancel }: {
  week: WorkDay[];
  barberName: string;
  save: (days: WorkDayInput[]) => Promise<unknown>;
  onCancel: () => void;
}) => {
  const [initial] = useState(() => weekFields(week));
  const [days, setDays] = useState(initial);

  const change = (index: number, changes: Partial<DayFields>) =>
    setDays((current) => current.map((d, i) => (i === index ? { ...d, ...changes } : d)));

  const submit = async () => {
    if (JSON.stringify(days) === JSON.stringify(initial)) return false;
    await save(days.map(dayInput));
    return true;
  };

  return (
    <AdminForm
      title={`Escala de ${barberName}`}
      submitLabel="Salvar escala"
      errorFallback="Não foi possível salvar a escala."
      validate={() => validateWeek(days)}
      save={submit}
      onCancel={onCancel}
    >
      <div className={styles.wide}>
        <table className={shared.table}>
          <thead>
            <tr>
              <th>Dia</th>
              <th>Trabalha</th>
              <th>Início</th>
              <th>Fim</th>
              <th>Almoço (início)</th>
              <th>Almoço (fim)</th>
            </tr>
          </thead>
          <tbody>
            {days.map((day, index) => {
              const name = DAY_NAMES[day.day_of_week];
              return (
                <tr key={day.day_of_week} aria-label={name}>
                  <td>{name}</td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`${name}: trabalha`}
                      checked={day.is_working}
                      onChange={(e) => change(index, { is_working: e.target.checked })}
                    />
                  </td>
                  {TIME_FIELDS.map(([key, label]) => (
                    <td key={key}>
                      <input
                        type="time"
                        aria-label={`${name}: ${label}`}
                        value={day[key]}
                        disabled={!day.is_working}
                        onChange={(e) => change(index, { [key]: e.target.value })}
                      />
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </AdminForm>
  );
};

const BarberSchedule = ({ barberId, barberName, onSaved, onCancel }: Props) => {
  const { week, status, loadError, reload, saveWeek } = useBarberSchedule(barberId);

  const save = async (days: WorkDayInput[]) => {
    await saveWeek(days);
    onSaved();
  };

  return (
    <LoadState status={status} loadError={loadError} reload={reload} loadingText="Carregando escala...">
      <WeekForm week={week} barberName={barberName} save={save} onCancel={onCancel} />
    </LoadState>
  );
};

export default BarberSchedule;
