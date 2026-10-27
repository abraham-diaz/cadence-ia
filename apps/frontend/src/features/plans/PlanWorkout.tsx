import { ChevronDown } from 'lucide-react'
import { useId, useState } from 'react'
import type { PlanDay } from '../../api/types.ts'
import ExerciseSuggestions from '../exercises/ExerciseSuggestions.tsx'
import PlannedExercises from '../exercises/PlannedExercises.tsx'
import './plan-workout.css'
import { workoutName } from './weeks.ts'

/** A workout of the plan; its exercises and note fold out underneath. With `suggestOn`
    (a date), strength workouts without exercises suggest some from the catalog. */
export default function PlanWorkout({
  workout,
  suggestOn,
  done = false,
}: {
  workout: PlanDay
  suggestOn?: string
  done?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [tapped, setTapped] = useState(false)
  const panelId = useId()
  const suggest =
    suggestOn !== undefined && workout.exercises.length === 0 && workout.workout_type?.category === 'strength'
  const foldable = workout.exercises.length > 0 || !!workout.note || suggest

  const summary = (
    <>
      <span className="workout-text">
        <span className="workout-title">{workoutName(workout)}</span>
        <span className="muted small">{describe(workout)}</span>
      </span>
      {done && <span className="done-badge">✓</span>}
    </>
  )

  return (
    <div className={`workout stripe-${workout.workout_type?.category ?? 'none'}`}>
      {foldable ? (
        <button
          type="button"
          className="workout-row workout-toggle"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => {
            setOpen(!open)
            setTapped(true)
          }}
        >
          {summary}
          <ChevronDown size={20} className={`workout-chevron${open ? ' open' : ''}`} aria-hidden="true" />
        </button>
      ) : (
        <div className="workout-row">{summary}</div>
      )}
      {open && (
        <div id={panelId} className={`workout-panel${tapped ? ' fold-out' : ''}`}>
          {suggest && workout.workout_type ? (
            <ExerciseSuggestions type={workout.workout_type} today={suggestOn} />
          ) : (
            workout.exercises.length > 0 && <PlannedExercises exercises={workout.exercises} />
          )}
          {workout.note && <p className="muted small">{workout.note}</p>}
        </div>
      )}
    </div>
  )
}

function describe(workout: PlanDay): string {
  const parts = [`${workout.minutes} min`]
  const count = workout.exercises.length
  if (count) parts.push(count === 1 ? '1 ejercicio' : `${count} ejercicios`)
  return parts.join(' · ')
}
