import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { fetchCurrentPlan } from '../../api/plans.ts'
import type { Plan, PlanDay } from '../../api/types.ts'
import { useFetch } from '../../shared/useFetch.ts'
import { fromPlan, loadDraft, saveDraft } from './planDraft.ts'
import './plans.css'
import { describeDay, todayWeekday, WEEKDAYS, weekLetter } from './weeks.ts'

export default function PlanPage() {
  const { state } = useFetch(fetchCurrentPlan, 'current-plan')

  return (
    <main className="page">
      <nav className="top-bar chat-top-bar">
        <Link to="/" className="back-link">
          ‹ Entrenamientos
        </Link>
        <Link to="/plan/nuevo" className="link-button">
          Nuevo plan
        </Link>
      </nav>

      {state.status === 'loading' && <p className="muted">Cargando…</p>}
      {state.status === 'error' && <p className="notice">No se pudo cargar el plan ({state.error}).</p>}
      {state.status === 'ok' && !state.data && (
        <>
          <header className="page-header">
            <p className="eyebrow">Plan</p>
            <h1>Sin plan</h1>
          </header>
          <p className="notice">Aún no tienes un plan. Diséñalo con el entrenador IA.</p>
          <Link to="/plan/nuevo" className="button">
            Nuevo plan de entrenamiento
          </Link>
        </>
      )}
      {state.status === 'ok' && state.data && <PlanView plan={state.data} />}
    </main>
  )
}

function PlanView({ plan }: { plan: Plan }) {
  const [week, setWeek] = useState(plan.current_week)
  const navigate = useNavigate()
  const today = todayWeekday()
  const weeks = Array.from({ length: plan.weeks }, (_, i) => i)

  function edit() {
    const pending = loadDraft()
    if (pending && pending.source !== 'plan') {
      if (!window.confirm('Tienes un plan del chat sin guardar. ¿Lo descartas para editar el actual?')) return
    }
    // Unsaved edits of this same plan are kept: tapping "Editar" again doesn't lose them.
    if (pending?.source !== 'plan') saveDraft(fromPlan(plan))
    navigate('/plan/revisar')
  }

  return (
    <>
      <header className="page-header">
        <p className="eyebrow">Plan</p>
        <h1>{plan.title}</h1>
        {plan.weeks > 1 && (
          <p className="muted">
            Esta semana toca la {weekLetter(plan.current_week)} (de {plan.weeks})
          </p>
        )}
      </header>

      <button type="button" className="button button-secondary" onClick={edit}>
        Editar plan
      </button>

      {plan.weeks > 1 && (
        <div
          className="segmented"
          role="tablist"
          aria-label="Semana"
          style={{ gridTemplateColumns: `repeat(${plan.weeks}, 1fr)` }}
        >
          {weeks.map((w) => (
            <button
              key={w}
              type="button"
              role="tab"
              aria-selected={week === w}
              className={week === w ? 'selected' : ''}
              onClick={() => setWeek(w)}
            >
              Semana {weekLetter(w)}
            </button>
          ))}
        </div>
      )}

      <ol className="plan-week">
        {WEEKDAYS.map((name, weekday) => {
          const days = plan.days.filter((d) => d.week === week && d.weekday === weekday)
          const isToday = week === plan.current_week && weekday === today
          return (
            <li key={name} className={`card plan-weekday${isToday ? ' plan-today' : ''}`}>
              <p className="plan-weekday-name">
                {name}
                {isToday && <span className="chip">Hoy</span>}
              </p>
              {days.length === 0 ? <p className="muted">Descanso</p> : days.map((day, i) => <DayView key={i} day={day} />)}
            </li>
          )
        })}
      </ol>
    </>
  )
}

function DayView({ day }: { day: PlanDay }) {
  const summary = <span className="plan-day-title">{describeDay(day)}</span>
  if (!day.exercises.length && !day.note) return <p>{summary}</p>

  return (
    <details className="plan-day">
      <summary>{summary}</summary>
      {day.exercises.length > 0 && (
        <ul className="plan-exercises">
          {day.exercises.map((e, i) => (
            <li key={i}>
              {e.name}
              {(e.sets || e.reps) && (
                <span className="muted">
                  {' '}
                  · {[e.sets && `${e.sets} series`, e.reps && `${e.reps} reps`].filter(Boolean).join(' × ')}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      {day.note && <p className="muted small">{day.note}</p>}
    </details>
  )
}
