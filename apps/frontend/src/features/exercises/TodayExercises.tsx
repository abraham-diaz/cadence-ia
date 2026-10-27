import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router'
import type { Exercise, WeekProgress } from '../../api/types.ts'
import './exercises.css'

/** The exercises the plan sets for today; the ones in the catalog open how they're done. */
export default function TodayExercises({ progress, today }: { progress: WeekProgress; today: string }) {
  const planned = progress.days.find((d) => d.date === today)?.planned ?? []
  const exercises = planned.flatMap((p) => p.exercises)
  if (exercises.length === 0) return null

  return (
    <section className="card exercises-card">
      <p className="today-kicker">Ejercicios de hoy</p>
      <ul className="exercise-items">
        {exercises.map((exercise, i) => (
          <li key={i}>
            {exercise.catalog_id ? (
              <Link to={`/ejercicio/${exercise.catalog_id}`} className="exercise-row exercise-link">
                <Row exercise={exercise} />
                <ChevronRight size={18} className="exercise-chevron" aria-hidden="true" />
              </Link>
            ) : (
              <div className="exercise-row">
                <Row exercise={exercise} />
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}

function Row({ exercise }: { exercise: Exercise }) {
  const amount = [exercise.sets && `${exercise.sets} series`, exercise.reps && `${exercise.reps} reps`]
    .filter(Boolean)
    .join(' × ')
  return (
    <>
      {exercise.image_url ? (
        <img src={exercise.image_url} alt="" loading="lazy" className="exercise-thumb" />
      ) : (
        // Without a catalog entry there's nothing to open: no empty box that looks tappable.
        exercise.catalog_id && <span className="exercise-thumb" aria-hidden="true" />
      )}
      <span className="exercise-text">
        <span>{exercise.name}</span>
        {amount && <span className="muted small">{amount}</span>}
      </span>
    </>
  )
}
