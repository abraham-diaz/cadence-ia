import { ChevronRight } from 'lucide-react'
import type { CSSProperties } from 'react'
import { Link } from 'react-router'
import type { SessionSummary } from '../../api/types.ts'
import { formatMinutes, formatTime } from '../../shared/format.ts'

/** What was trained on the day tapped in the week strip; the caret points at that day. */
export default function DaySessions({ sessions, weekday }: { sessions: SessionSummary[]; weekday: number }) {
  return (
    <ul className="day-sessions" style={{ '--caret': `${((weekday + 0.5) / 7) * 100}%` } as CSSProperties}>
      {sessions.map((session) => {
        const type = session.workout_type
        return (
          <li key={session.id}>
            <Link to={`/sesion/${session.id}`} className={`day-session stripe-${type?.category ?? 'none'}`}>
              <span className="day-session-main">
                <span className={type ? 'day-session-title' : 'day-session-title pending'}>
                  {type?.name ?? 'Sin clasificar'}
                </span>
                <span className="muted small">{formatTime(session.start_time)}</span>
              </span>
              <span className="day-session-stats">
                {formatMinutes(session.duration_s)} · {session.hr_avg} <small>ppm</small>
              </span>
              <ChevronRight size={18} className="day-session-chevron" aria-hidden="true" />
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
