import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router'
import { fetchWeekProgress } from '../../api/plans.ts'
import { fetchSessions } from '../../api/sessions.ts'
import type { SessionSummary } from '../../api/types.ts'
import ExerciseSuggestions from '../exercises/ExerciseSuggestions.tsx'
import TodayExercises from '../exercises/TodayExercises.tsx'
import { formatDay, localIsoDate, mondayOf, todayIso } from '../../shared/format.ts'
import { useFetch } from '../../shared/useFetch.ts'
import './home.css'
import TodayCard from './TodayCard.tsx'
import WeekCarousel from './WeekCarousel.tsx'

export default function HomePage() {
  const sessions = useFetch(fetchSessions, 'sessions')
  const progress = useFetch(() => fetchWeekProgress(), 'week-progress')
  const refreshing = sessions.refreshing || progress.refreshing
  const today = todayIso()
  const list = sessions.state.status === 'ok' ? sessions.state.data : []
  const byId = new Map(list.map((s) => [s.id, s]))
  const oldest = list.at(-1)

  function reload() {
    sessions.reload()
    progress.reload()
  }

  return (
    <main className="page">
      <header className="page-header page-header-row">
        <div>
          <p className="eyebrow">{formatDay(`${today}T12:00:00`)}</p>
          <h1>Hoy</h1>
        </div>
        <button
          type="button"
          className="button button-secondary button-small icon-button"
          onClick={reload}
          disabled={refreshing}
          aria-label="Actualizar"
        >
          <span className={refreshing ? 'spin' : ''} aria-hidden="true">
            ↻
          </span>
        </button>
      </header>

      {progress.state.status === 'loading' && (
        <>
          <div className="card skeleton skeleton-today" />
          <div className="card skeleton skeleton-week" />
        </>
      )}
      {progress.state.status === 'error' && (
        <p className="notice">No se pudo cargar el plan de esta semana ({progress.state.error}).</p>
      )}
      {progress.state.status === 'ok' && (
        <>
          <TodayCard progress={progress.state.data} today={today} />
          <TodayExercises progress={progress.state.data} today={today} />
          <ExerciseSuggestions progress={progress.state.data} today={today} />
          <WeekCarousel
            current={progress.state.data}
            firstWeek={oldest ? localIsoDate(mondayOf(new Date(oldest.start_time))) : progress.state.data.start}
            today={today}
            sessions={byId}
          />
        </>
      )}

      {sessions.state.status === 'error' && (
        <p className="notice">No se pudieron cargar los entrenamientos ({sessions.state.error}).</p>
      )}
      {sessions.state.status === 'ok' && (
        <>
          <UnclassifiedNotice sessions={sessions.state.data} />
          {sessions.state.data.length === 0 && (
            <p className="notice">Aún no hay entrenamientos. Exporta uno desde el reloj.</p>
          )}
        </>
      )}
    </main>
  )
}

/** Without a type a session has no sets, recovery or assessment: worth a reminder. */
function UnclassifiedNotice({ sessions }: { sessions: SessionSummary[] }) {
  const pending = sessions.filter((s) => !s.workout_type)
  if (pending.length === 0) return null

  return (
    <Link to={`/sesion/${pending[0].id}`} className="card unclassified-notice">
      <span className="unclassified-icon" aria-hidden="true">
        !
      </span>
      <span className="unclassified-text">
        <strong>
          {pending.length === 1 ? '1 sesión sin clasificar' : `${pending.length} sesiones sin clasificar`}
        </strong>
        <span className="muted small">Ponle un tipo para ver series, recuperación y valoración.</span>
      </span>
      <ChevronRight size={20} className="unclassified-chevron" aria-hidden="true" />
    </Link>
  )
}
