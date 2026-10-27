import { useNavigate, useParams } from 'react-router'
import { fetchExercise } from '../../api/exercises.ts'
import type { ExerciseDetail } from '../../api/types.ts'
import { useFetch } from '../../shared/useFetch.ts'
import './exercises.css'

/** How an exercise is done: picture, steps and muscles, from the wger catalog. */
export default function ExerciseDetailPage() {
  const id = Number(useParams().id)
  const navigate = useNavigate()
  const { state } = useFetch(() => fetchExercise(id), `exercise:${id}`)
  // Opened from a link inside the app, go back there; opened directly, go home.
  const canGoBack = (window.history.state?.idx ?? 0) > 0

  return (
    <main className="page">
      <nav className="top-bar">
        <button type="button" className="back-link link-button" onClick={() => (canGoBack ? navigate(-1) : navigate('/'))}>
          ‹ Volver
        </button>
      </nav>

      {state.status === 'loading' && <p className="muted">Cargando…</p>}
      {state.status === 'error' && <p className="notice">No se pudo cargar el ejercicio ({state.error}).</p>}
      {state.status === 'ok' && <Detail exercise={state.data} />}
    </main>
  )
}

function Detail({ exercise }: { exercise: ExerciseDetail }) {
  const steps = exercise.description?.split('\n') ?? []

  return (
    <>
      <header className="page-header">
        <p className="eyebrow">Ejercicio</p>
        <h1>{exercise.name}</h1>
      </header>

      {exercise.image_url && <img src={exercise.image_url} alt="" className="exercise-picture" />}

      <section className="card exercise-section">
        <h2 className="section-title">Músculos</h2>
        <div className="chip-row">
          {exercise.primary_muscles.map((m) => (
            <span key={m.id} className="chip">
              {m.name}
            </span>
          ))}
          {exercise.secondary_muscles.map((m) => (
            <span key={m.id} className="chip chip-pending">
              {m.name}
            </span>
          ))}
        </div>
        {exercise.secondary_muscles.length > 0 && (
          <p className="muted small">Con borde discontinuo, los que trabaja de forma secundaria.</p>
        )}
      </section>

      <section className="card exercise-section">
        <h2 className="section-title">Cómo se hace</h2>
        {steps.length > 0 ? (
          steps.map((step, i) => <p key={i}>{step}</p>)
        ) : (
          <p className="muted">wger no tiene instrucciones para este ejercicio.</p>
        )}
      </section>

      <p className="exercise-credit">
        De{' '}
        <a href={`https://wger.de/exercise/${exercise.id}/view-base`} target="_blank" rel="noreferrer">
          wger.de
        </a>
        {exercise.author && `, por ${exercise.author}`} · {exercise.license}
      </p>
    </>
  )
}
