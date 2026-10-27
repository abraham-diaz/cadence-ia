import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router'
import { fetchTypeExercises } from '../../api/exercises.ts'
import type { WeekProgress, WorkoutTypeRef } from '../../api/types.ts'
import { useFetch } from '../../shared/useFetch.ts'
import './exercises.css'

/** Catalog exercises for today's strength workouts, when the plan doesn't list its own. */
export default function ExerciseSuggestions({ progress, today }: { progress: WeekProgress; today: string }) {
  const planned = progress.days.find((d) => d.date === today)?.planned ?? []
  const types = planned
    .filter((p) => p.workout_type?.category === 'strength' && p.exercises.length === 0)
    .map((p) => p.workout_type as WorkoutTypeRef)

  return types.map((type) => <TypeSuggestions key={type.id} type={type} today={today} />)
}

function TypeSuggestions({ type, today }: { type: WorkoutTypeRef; today: string }) {
  const { state } = useFetch(() => fetchTypeExercises(type.id, today), `exercises:${type.id}:${today}`)
  if (state.status !== 'ok') return null

  if (state.data.length === 0) {
    return (
      <Link to="/tipos" className="card exercises-card exercises-hint">
        <p className="today-kicker">Ejercicios</p>
        <p className="muted small">Elige en Tipos qué músculos trabaja «{type.name}» y aquí te propondré ejercicios.</p>
      </Link>
    )
  }

  const groups = state.data.filter((s) => s.exercises.length > 0)
  if (groups.length === 0) return null // the catalog hasn't been downloaded yet

  return (
    <section className="card exercises-card">
      <p className="today-kicker">Ejercicios para {type.name}</p>
      {groups.map(({ muscle, exercises }) => (
        <div key={muscle.id} className="exercise-group">
          <h3>{muscle.name}</h3>
          <ul className="exercise-items">
            {exercises.map((exercise) => (
              <li key={exercise.id}>
                <Link to={`/ejercicio/${exercise.id}`} className="exercise-row exercise-link">
                  {exercise.image_url ? (
                    <img src={exercise.image_url} alt="" loading="lazy" className="exercise-thumb" />
                  ) : (
                    <span className="exercise-thumb" aria-hidden="true" />
                  )}
                  <span className="exercise-text">{exercise.name}</span>
                  <ChevronRight size={18} className="exercise-chevron" aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <p className="exercise-credit">
        Ejercicios de{' '}
        <a href="https://wger.de" target="_blank" rel="noreferrer">
          wger.de
        </a>{' '}
        (CC BY-SA)
      </p>
    </section>
  )
}
