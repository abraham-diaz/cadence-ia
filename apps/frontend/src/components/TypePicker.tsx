import { useState } from 'react'
import { createWorkoutType, fetchWorkoutTypes, type WorkoutTypeRef } from '../api.ts'
import { useFetch } from '../useFetch.ts'
import WorkoutTypeForm from './WorkoutTypeForm.tsx'

interface Props {
  current: WorkoutTypeRef | null
  onPick: (typeId: number) => Promise<void>
  onCancel?: () => void
}

/** "¿Qué entrenaste?": choose one of your types or create a new one. */
export default function TypePicker({ current, onPick, onCancel }: Props) {
  const { state } = useFetch(fetchWorkoutTypes, 'types')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function pick(typeId: number) {
    setError(null)
    try {
      await onPick(typeId)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const types = state.status === 'ok' ? state.data : []

  return (
    <section className="card picker">
      <div className="picker-head">
        <h2>¿Qué entrenaste?</h2>
        {onCancel && (
          <button type="button" className="link-button" onClick={onCancel}>
            Cerrar
          </button>
        )}
      </div>

      {state.status === 'loading' && <p className="muted small">Cargando tipos…</p>}
      {state.status === 'error' && <p className="form-error">{state.error}</p>}
      {state.status === 'ok' && types.length === 0 && !creating && (
        <p className="muted small">Aún no tienes tipos. Crea el primero.</p>
      )}

      {types.length > 0 && (
        <div className="chip-row">
          {types.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`chip chip-button ${current?.id === t.id ? 'selected' : ''}`}
              onClick={() => pick(t.id)}
            >
              {t.name}
            </button>
          ))}
        </div>
      )}

      {creating ? (
        <WorkoutTypeForm
          submitLabel="Crear y asignar"
          onCancel={() => setCreating(false)}
          onSubmit={async (input) => {
            const created = await createWorkoutType(input)
            await onPick(created.id)
          }}
        />
      ) : (
        <button type="button" className="button button-secondary" onClick={() => setCreating(true)}>
          + Nuevo tipo
        </button>
      )}
      {error && <p className="form-error">{error}</p>}
    </section>
  )
}
