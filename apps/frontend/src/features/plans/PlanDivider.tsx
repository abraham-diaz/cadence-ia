import { Link } from 'react-router'
import { fetchCurrentPlan } from '../../api/plans.ts'
import { useFetch } from '../../shared/useFetch.ts'
import { loadChat } from './chatStorage.ts'
import './plans.css'
import { describeDay, todayWeekday } from './weeks.ts'

/** A divider with today's plan in the middle, or a way to make one. */
export default function PlanDivider() {
  const { state } = useFetch(fetchCurrentPlan, 'current-plan')
  const plan = state.status === 'ok' ? state.data : null

  let to = '/plan/nuevo'
  let label = loadChat().length > 0 ? 'Seguir con el plan' : 'Nuevo plan'
  if (plan) {
    const today = plan.days.filter((d) => d.week === plan.current_week && d.weekday === todayWeekday())
    to = '/plan'
    label = today.length ? `Hoy: ${today.map(describeDay).join(' + ')}` : 'Hoy: descanso'
  }

  return (
    <div className="plan-divider">
      {state.status !== 'loading' && (
        <Link to={to} className="chip chip-button plan-divider-link">
          {label}
        </Link>
      )}
    </div>
  )
}
