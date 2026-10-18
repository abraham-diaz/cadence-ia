import { lazy, Suspense, useState } from 'react'
import { Link, useParams } from 'react-router'
import {
  CATEGORY_LABELS,
  fetchSession,
  setSessionType,
  type SessionDetail,
  type SessionStats,
} from '../api.ts'
import AssessmentCard from '../components/AssessmentCard.tsx'
import Evolution from '../components/Evolution.tsx'
import SegmentList from '../components/SegmentList.tsx'
import Stat from '../components/Stat.tsx'
import TypePicker from '../components/TypePicker.tsx'
import { formatClock, formatDay, formatTime } from '../format.ts'
import { useFetch } from '../useFetch.ts'

// ECharts is heavy: load it only when a session is opened, not on the list.
const HeartRateChart = lazy(() => import('../components/HeartRateChart.tsx'))

export default function SessionDetailPage() {
  const { id = '' } = useParams()
  const { state, setData } = useFetch(() => fetchSession(id), id)

  return (
    <main className="page">
      <nav className="top-bar">
        <Link to="/" className="back-link">
          ‹ Entrenamientos
        </Link>
      </nav>

      {state.status === 'loading' && <p className="muted">Cargando…</p>}
      {state.status === 'error' && <p className="notice">No se pudo cargar la sesión ({state.error}).</p>}
      {state.status === 'ok' && <Detail session={state.data} onChange={setData} />}
    </main>
  )
}

function Detail({ session, onChange }: { session: SessionDetail; onChange: (s: SessionDetail) => void }) {
  const [picking, setPicking] = useState(false)
  const type = session.workout_type
  const isStrength = type?.category === 'strength'

  const { stats, comparison: base } = session
  // Difference with the average of previous sessions of this type, if any.
  const delta = (key: keyof SessionStats, scale = 1) => {
    const now = stats[key]
    const before = base?.[key]
    return now === null || before === null || before === undefined ? null : (now - before) / scale
  }

  async function pick(typeId: number) {
    onChange(await setSessionType(session.id, typeId))
    setPicking(false)
  }

  return (
    <>
      <header className="page-header">
        <p className="eyebrow">{formatTime(session.start_time)}</p>
        <h1>{formatDay(session.start_time)}</h1>
        {type && !picking && (
          <p className="type-line">
            <span className="chip">{type.name}</span>
            <span className="muted small">{CATEGORY_LABELS[type.category]}</span>
            <button type="button" className="link-button" onClick={() => setPicking(true)}>
              Cambiar
            </button>
          </p>
        )}
      </header>

      {(!type || picking) && (
        <TypePicker current={type} onPick={pick} onCancel={type ? () => setPicking(false) : undefined} />
      )}

      {base && (
        <p className="muted small compare-note">
          Comparado con tu media de {base.sessions === 1 ? 'la sesión anterior' : `las ${base.sessions} anteriores`}{' '}
          de {type?.name}
        </p>
      )}
      <section className="stat-grid" aria-label="Resumen">
        <Stat label="Duración" value={formatClock(session.duration_s)} delta={delta('duration_s', 60)} deltaUnit=" min" />
        <Stat label="FC media" value={session.hr_avg} unit="ppm" delta={delta('hr_avg')} />
        <Stat label="FC máx." value={session.hr_max} unit="ppm" delta={delta('hr_max')} />
        {isStrength && (
          <>
            <Stat label="Series" value={session.sets ?? '–'} delta={delta('sets')} />
            <Stat
              label="Descanso medio"
              value={stats.avg_rest_s === null ? '–' : formatClock(stats.avg_rest_s)}
              delta={delta('avg_rest_s')}
              deltaUnit=" s"
            />
            <Stat
              label="Recup. a 30 s"
              value={stats.recovery_30s === null ? '–' : `−${Math.round(stats.recovery_30s)}`}
              unit={stats.recovery_30s === null ? undefined : 'ppm'}
              delta={delta('recovery_30s')}
            />
          </>
        )}
      </section>

      {type && (
        <AssessmentCard
          sessionId={session.id}
          assessment={session.assessment}
          onChange={(assessment) => onChange({ ...session, assessment })}
        />
      )}

      <section className="card chart-card">
        <div className="chart-head">
          <h2>Pulso</h2>
          {isStrength && (
            <p className="legend">
              <span className="legend-swatch" aria-hidden="true" /> Serie
            </p>
          )}
        </div>
        <Suspense fallback={<div className="hr-chart" />}>
          <HeartRateChart points={session.heart_rate} segments={session.segments} />
        </Suspense>
        <p className="muted small">Pellizca para hacer zoom · {session.calories} kcal (estimadas)</p>
      </section>

      <Evolution session={session} />

      {isStrength && (
        <section>
          <h2 className="section-title">Series y descansos</h2>
          <SegmentList segments={session.segments} />
        </section>
      )}
    </>
  )
}
