import { Link } from 'react-router'
import { fetchSessions, type SessionSummary } from '../api.ts'
import { formatDay, formatMinutes, formatTime } from '../format.ts'
import { useFetch } from '../useFetch.ts'

export default function SessionListPage() {
  const { state } = useFetch(fetchSessions, 'sessions')

  return (
    <main className="page">
      <header className="page-header page-header-row">
        <div>
          <p className="eyebrow">Cadence</p>
          <h1>Entrenamientos</h1>
        </div>
        <Link to="/tipos" className="button button-secondary button-small">
          Tipos
        </Link>
      </header>

      {state.status === 'loading' && <p className="muted">Cargando…</p>}
      {state.status === 'error' && (
        <p className="notice">No se pudieron cargar los entrenamientos ({state.error}).</p>
      )}
      {state.status === 'ok' && state.data.length === 0 && (
        <p className="notice">Aún no hay entrenamientos. Exporta uno desde el reloj.</p>
      )}
      {state.status === 'ok' && (
        <ul className="session-list">
          {state.data.map((session) => (
            <li key={session.id}>
              <SessionCard session={session} />
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}

function SessionCard({ session }: { session: SessionSummary }) {
  const type = session.workout_type

  return (
    <Link to={`/sesion/${session.id}`} className="card session-card">
      <div className="session-card-top">
        <div>
          <p className="session-day">{formatDay(session.start_time)}</p>
          <p className="muted small">
            {formatTime(session.start_time)} · {formatMinutes(session.duration_s)}
          </p>
        </div>
        <span className="chevron" aria-hidden="true">
          ›
        </span>
      </div>
      <p className="session-type">
        {type ? <span className="chip">{type.name}</span> : <span className="chip chip-pending">Sin clasificar</span>}
      </p>
      <dl className="session-card-stats">
        <div>
          <dt>FC media</dt>
          <dd>
            {session.hr_avg} <small>ppm</small>
          </dd>
        </div>
        <div>
          <dt>FC máx.</dt>
          <dd>
            {session.hr_max} <small>ppm</small>
          </dd>
        </div>
        {session.sets !== null ? (
          <div>
            <dt>Series</dt>
            <dd>{session.sets}</dd>
          </div>
        ) : (
          <div>
            <dt>Energía</dt>
            <dd>
              {session.calories} <small>kcal</small>
            </dd>
          </div>
        )}
      </dl>
    </Link>
  )
}
