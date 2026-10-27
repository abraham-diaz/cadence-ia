import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router'
import { fetchTypeExercises } from '../../api/exercises.ts'
import type { WorkoutTypeRef } from '../../api/types.ts'
import { useFetch } from '../../shared/useFetch.ts'
import './exercises.css'

/** Catalog exercises for a strength workout the plan doesn't list its own for. */
export default function ExerciseSuggestions({ type, today }: { type: WorkoutTypeRef; today: string }) {
  const { state } = useFetch(() => fetchTypeExercises(type.id, today), `exercises:${type.id}:${today}`)
  if (state.status === 'loading') return <p className="muted small">Cargando ejercicios…</p>
  if (state.status === 'error') return <p className="muted small">No se pudieron cargar los ejercicios.</p>

  if (state.data.length === 0) {
    return (
      <Link to="/tipos" className="exercises-hint muted small">
        Elige en Tipos qué músculos trabaja «{type.name}» y aquí te propondré ejercicios.
      </Link>
    )
  }

  const groups = state.data.filter((s) => s.exercises.length > 0)
  if (groups.length === 0) return <p className="muted small">El catálogo de ejercicios aún no se ha descargado.</p>

  return (
    <>
      {groups.map(({ muscle, exercises }) => (
        <div key={muscle.id} className="exercise-group">
          <h3>{muscle.name}</h3>
          <ul className="exercise-items">
            {exercises.map((exercise) => (
              <li key={exercise.id}>
                <Link to={`/ejercicio/${exercise.id}`} className="exercise-row exercise-link">
                  {exercise.image_url ? (
                    <img src={exercise.image_url} alt="" decoding="sync" className="exercise-thumb" />
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
    </>
  )
}
