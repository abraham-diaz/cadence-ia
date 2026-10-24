import { useState } from 'react'
import type { WorkoutType } from '../../api/types.ts'
import {
  createWorkoutType,
  deleteWorkoutType,
  fetchWorkoutTypes,
  updateWorkoutType,
} from '../../api/workoutTypes.ts'
import { useFetch } from '../../shared/useFetch.ts'
import { CATEGORY_LABELS } from './categories.ts'
import WorkoutTypeForm from './WorkoutTypeForm.tsx'
import './workout-types.css'

export default function WorkoutTypesPage() {
  const { state, reload } = useFetch(fetchWorkoutTypes, 'types')
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function remove(type: WorkoutType) {
    const sessions =
      type.session_count === 1 ? '1 sesión quedará' : `${type.session_count} sesiones quedarán`
    const warning = type.session_count ? `\n${sessions} sin clasificar.` : ''
    if (!window.confirm(`¿Borrar «${type.name}»?${warning}`)) return
    setError(null)
    try {
      await deleteWorkoutType(type.id)
      reload()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <main className="page">
      <header className="page-header">
        <p className="eyebrow">Ajustes</p>
        <h1>Tipos de entrenamiento</h1>
      </header>

      {state.status === 'loading' && <p className="muted">Cargando…</p>}
      {state.status === 'error' && <p className="notice">No se pudieron cargar los tipos ({state.error}).</p>}
      {error && <p className="form-error">{error}</p>}

      {state.status === 'ok' && state.data.length > 0 && (
        <ul className="type-list">
          {state.data.map((type) => (
            <li key={type.id} className="type-row">
              {editingId === type.id ? (
                <WorkoutTypeForm
                  initial={type}
                  submitLabel="Guardar"
                  onCancel={() => setEditingId(null)}
                  onSubmit={async (input) => {
                    await updateWorkoutType(type.id, input)
                    setEditingId(null)
                    reload()
                  }}
                />
              ) : (
                <>
                  <div>
                    <p className="type-name">{type.name}</p>
                    <p className="muted small">
                      {CATEGORY_LABELS[type.category]} ·{' '}
                      {type.session_count === 1 ? '1 sesión' : `${type.session_count} sesiones`}
                    </p>
                  </div>
                  <div className="row-actions">
                    <button type="button" className="link-button" onClick={() => setEditingId(type.id)}>
                      Editar
                    </button>
                    <button type="button" className="link-button danger" onClick={() => remove(type)}>
                      Borrar
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {state.status === 'ok' && state.data.length === 0 && !creating && (
        <p className="notice">Aún no tienes tipos. Crea uno, o hazlo al abrir un entrenamiento.</p>
      )}

      {creating ? (
        <section className="card picker">
          <h2 className="section-title">Nuevo tipo</h2>
          <WorkoutTypeForm
            submitLabel="Crear"
            onCancel={() => setCreating(false)}
            onSubmit={async (input) => {
              await createWorkoutType(input)
              setCreating(false)
              reload()
            }}
          />
        </section>
      ) : (
        <button type="button" className="button" onClick={() => setCreating(true)}>
          + Nuevo tipo
        </button>
      )}
    </main>
  )
}
