import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { fetchCurrentPlan } from '../../api/plans.ts'
import type { Plan } from '../../api/types.ts'
import { useFetch } from '../../shared/useFetch.ts'
import { fromPlan, loadDraft, saveDraft } from './planDraft.ts'
import './plans.css'
import PlanWorkout from './PlanWorkout.tsx'
import WeekTabs from './WeekTabs.tsx'
import { todayWeekday, WEEKDAYS, weekLetter } from './weeks.ts'

export default function PlanPage() {
  const { state } = useFetch(fetchCurrentPlan, 'current-plan')

  return (
    <main className="page">
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

      <div className="plan-actions">
        <button type="button" className="button button-secondary" onClick={edit}>
          Editar plan
        </button>
        <Link to="/plan/nuevo" className="button button-secondary">
          Nuevo plan
        </Link>
      </div>

      <WeekTabs weeks={plan.weeks} selected={week} onSelect={setWeek} />

      <ol className="card plan-week">
        {WEEKDAYS.map((name, weekday) => {
          const days = plan.days.filter((d) => d.week === week && d.weekday === weekday)
          const isToday = week === plan.current_week && weekday === today
          return (
            <li key={name} className={`plan-weekday${days.length === 0 ? ' rest' : ''}${isToday ? ' today' : ''}`}>
              <span className="plan-weekday-name" aria-label={isToday ? `${name}, hoy` : name}>
                {name.slice(0, 3)}
              </span>
              {days.length === 0 ? (
                <span className="muted small">Descanso</span>
              ) : (
                <div className="plan-workouts">
                  {days.map((day, i) => (
                    <PlanWorkout key={i} workout={day} />
                  ))}
                </div>
              )}
            </li>
          )
        })}
      </ol>
    </>
  )
}
