import { lazy, Suspense } from 'react'
import type { SessionDetail, SessionStats } from '../api.ts'

const TrendChart = lazy(() => import('./TrendChart.tsx'))

interface Metric {
  key: keyof SessionStats
  title: string
  unit: string
  hint?: string
}

const COMMON: Metric[] = [{ key: 'hr_avg', title: 'FC media', unit: 'ppm' }]
const STRENGTH: Metric[] = [
  {
    key: 'recovery_30s',
    title: 'Recuperación a 30 s',
    unit: 'ppm',
    hint: 'Cuánto baja el pulso en los primeros 30 s de descanso. Más es mejor.',
  },
]

/** How this workout type has evolved, session by session. */
export default function Evolution({ session }: { session: SessionDetail }) {
  const type = session.workout_type
  if (!type) return null

  if (session.history.length < 2) {
    return (
      <section className="card evolution">
        <h2>Evolución · {type.name}</h2>
        <p className="muted small">
          Es tu primera sesión de {type.name}. Con la siguiente empezarás a ver aquí cómo progresas.
        </p>
      </section>
    )
  }

  const metrics = type.category === 'strength' ? [...COMMON, ...STRENGTH] : COMMON

  return (
    <section className="card evolution">
      <h2>Evolución · {type.name}</h2>
      <p className="muted small">
        {session.history.length} sesiones · el punto grande es esta
      </p>
      {metrics.map((m) => (
        <div key={m.key} className="trend">
          <h3>
            {m.title} <small>({m.unit})</small>
          </h3>
          {m.hint && <p className="muted small">{m.hint}</p>}
          <Suspense fallback={<div className="trend-chart" />}>
            <TrendChart history={session.history} currentId={session.id} metric={m.key} unit={m.unit} />
          </Suspense>
        </div>
      ))}
    </section>
  )
}
