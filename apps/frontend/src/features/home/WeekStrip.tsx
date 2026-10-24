import { useState } from 'react'
import type { DayStatus, SessionSummary, WeekProgress } from '../../api/types.ts'
import { WEEKDAYS, weekLetter } from '../plans/weeks.ts'
import DaySessions from './DaySessions.tsx'

const LETTERS = ['L', 'M', 'X', 'J', 'V', 'S', 'D']

// Six states from the API, three on screen: trained, had to train, rest.
const LOOKS: Record<DayStatus, string> = {
  done: 'trained',
  partial: 'trained',
  extra: 'trained',
  missed: 'planned',
  pending: 'planned',
  rest: 'rest',
}

const STATUS_LABELS: Record<DayStatus, string> = {
  done: 'hecho',
  partial: 'hecho a medias',
  missed: 'no hecho',
  pending: 'pendiente',
  rest: 'descanso',
  extra: 'entreno fuera del plan',
}

interface Props {
  progress: WeekProgress
  today: string
  sessions: Map<string, SessionSummary>
}

/** One week, Monday to Sunday: a dot per day with what was planned against what was done.
 * Tapping a day trained shows its sessions. */
export default function WeekStrip({ progress, today, sessions }: Props) {
  const [open, setOpen] = useState<number | null>(null)
  const hasPlan = progress.planned_sessions > 0
  const trained = progress.days.reduce((n, d) => n + d.session_ids.length, 0)
  const letter =
    progress.plan_weeks && progress.plan_weeks > 1 && progress.plan_week !== null
      ? `Semana ${weekLetter(progress.plan_week)} · `
      : ''

  return (
    <>
      <p className="week-totals">
        {letter}
        {hasPlan ? (
          <>
            <strong>
              {progress.done_sessions}/{progress.planned_sessions}
            </strong>{' '}
            sesiones · <strong>{progress.done_minutes}</strong>/{progress.planned_minutes} min
          </>
        ) : (
          <>
            <strong>{trained}</strong> {trained === 1 ? 'sesión' : 'sesiones'} · <strong>{progress.done_minutes}</strong>{' '}
            min
          </>
        )}
      </p>

      <ol className="week-strip">
        {progress.days.map((day, i) => (
          <li
            key={day.date}
            className={day.date === today ? 'week-day today' : 'week-day'}
            aria-label={day.session_ids.length ? undefined : `${WEEKDAYS[i]}: ${STATUS_LABELS[day.status]}`}
          >
            {day.session_ids.length > 0 ? (
              <button
                type="button"
                className={`week-dot dot-${LOOKS[day.status]}${open === i ? ' open' : ''}`}
                onClick={() => setOpen(open === i ? null : i)}
                aria-expanded={open === i}
                aria-label={`${WEEKDAYS[i]}: ${STATUS_LABELS[day.status]}`}
              >
                {LETTERS[i]}
              </button>
            ) : (
              <span className={`week-dot dot-${LOOKS[day.status]}`} aria-hidden="true">
                {LETTERS[i]}
              </span>
            )}
          </li>
        ))}
      </ol>

      <div className={hasPlan ? 'week-bar' : 'week-bar empty'} aria-hidden="true">
        {hasPlan && (
          <span style={{ width: `${Math.min(100, (100 * progress.done_minutes) / progress.planned_minutes)}%` }} />
        )}
      </div>

      {open !== null && (
        <DaySessions
          weekday={open}
          sessions={progress.days[open].session_ids.flatMap((id) => sessions.get(id) ?? [])}
        />
      )}
    </>
  )
}
