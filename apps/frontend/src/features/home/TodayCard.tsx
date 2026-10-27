import { Link } from 'react-router'
import type { WeekProgress } from '../../api/types.ts'
import { loadChat } from '../plans/chatStorage.ts'
import PlanWorkout from '../plans/PlanWorkout.tsx'
import { WEEKDAYS, workoutName } from '../plans/weeks.ts'

/** What the plan asks for today, or a way to make a plan. */
export default function TodayCard({ progress, today: date }: { progress: WeekProgress; today: string }) {
  if (!progress.plan_title) {
    return (
      <section className="card today-card">
        <p className="today-kicker">Sin plan</p>
        <p className="today-title">¿Qué toca hoy?</p>
        <p className="muted small">Diseña un plan con el entrenador y aquí verás lo de cada día.</p>
        <Link to="/plan/nuevo" className="button today-button">
          {loadChat().length > 0 ? 'Seguir con el plan' : 'Crear un plan'}
        </Link>
      </section>
    )
  }

  const index = progress.days.findIndex((d) => d.date === date)
  const today = progress.days[index]
  const planned = today?.planned ?? []

  if (planned.length === 0) {
    const next = progress.days.slice(index + 1).find((d) => d.planned.length > 0)
    return (
      <Link to="/plan" className="card today-card">
        <p className="today-kicker">Hoy toca</p>
        <p className="today-title">Descanso</p>
        <p className="muted small">
          {today?.session_ids.length
            ? 'Y aun así has entrenado.'
            : next
              ? `${WEEKDAYS[progress.days.indexOf(next)]}: ${next.planned.map(workoutName).join(' + ')}`
              : 'No queda nada más esta semana.'}
        </p>
      </Link>
    )
  }

  const allDone = planned.every((p) => p.done)
  return (
    <section className="card today-card">
      <div className="today-head">
        <p className="today-kicker">Hoy toca</p>
        {allDone && <span className="done-badge">✓ Hecho</span>}
      </div>
      <ul className="today-workouts">
        {planned.map((workout, i) => (
          <li key={i}>
            <PlanWorkout workout={workout} suggestOn={date} done={workout.done && !allDone} />
          </li>
        ))}
      </ul>
    </section>
  )
}
