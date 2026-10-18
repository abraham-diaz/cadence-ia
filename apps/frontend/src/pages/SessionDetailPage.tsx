import { lazy, Suspense, useState } from 'react'
import { Link, useParams } from 'react-router'
import { CATEGORY_LABELS, fetchSession, setSessionType, type SessionDetail } from '../api.ts'
import SegmentList from '../components/SegmentList.tsx'
import TypePicker from '../components/TypePicker.tsx'
import { average, formatClock, formatDay, formatTime } from '../format.ts'
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

  const rests = session.segments.filter((s) => s.kind === 'rest')
  const avgRest = average(rests.map((s) => s.duration_s))
  const avgDrop = average(rests.flatMap((s) => (s.drop_60s === null ? [] : [s.drop_60s])))

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

      <section className="stat-grid" aria-label="Resumen">
        <Stat label="Duración" value={formatClock(session.duration_s)} />
        <Stat label="FC media" value={session.hr_avg} unit="ppm" />
        <Stat label="FC máx." value={session.hr_max} unit="ppm" />
        {isStrength && (
          <>
            <Stat label="Series" value={session.sets ?? '–'} />
            <Stat label="Descanso medio" value={avgRest === null ? '–' : formatClock(avgRest)} />
            <Stat
              label="Recup. a 60 s"
              value={avgDrop === null ? '–' : `−${Math.round(avgDrop)}`}
              unit={avgDrop === null ? undefined : 'ppm'}
            />
          </>
        )}
      </section>

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

      {isStrength && (
        <section>
          <h2 className="section-title">Series y descansos</h2>
          <SegmentList segments={session.segments} />
        </section>
      )}
    </>
  )
}

function Stat({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="card stat">
      <p className="stat-label">{label}</p>
      <p className="stat-value">
        {value}
        {unit && <small> {unit}</small>}
      </p>
    </div>
  )
}
