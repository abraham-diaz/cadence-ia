import { useState } from 'react'
import type { WorkoutType } from '../../api/types.ts'
import ExerciseNameInput from '../exercises/ExerciseNameInput.tsx'
import { emptyExercise, sameName, type DraftDay, type DraftExercise } from './planDraft.ts'
import { WEEKDAYS } from './weeks.ts'

interface Props {
  day: DraftDay
  types: WorkoutType[]
  newTypes: { name: string; category: 'strength' | 'cardio' }[]
  onChange: (change: (day: DraftDay) => DraftDay) => void
  onRemove: () => void
}

const OTHER = 'other'

/** One training day of the plan being reviewed: everything is editable. */
export default function DayEditor({ day, types, newTypes, onChange, onRemove }: Props) {
  const [naming, setNaming] = useState(false)
  const [newName, setNewName] = useState('')

  const typeValue = day.type.kind === 'existing' ? `t:${day.type.id}` : `n:${day.type.name.trim().toLowerCase()}`

  function chooseType(value: string) {
    if (value === OTHER) {
      setNaming(true)
      return
    }
    setNaming(false)
    if (value.startsWith('t:')) {
      onChange((d) => ({ ...d, type: { kind: 'existing', id: Number(value.slice(2)) } }))
    } else {
      const chosen = newTypes.find((t) => sameName(t.name, value.slice(2)))
      if (chosen) onChange((d) => ({ ...d, type: { kind: 'new', ...chosen } }))
    }
  }

  function addNewType() {
    const name = newName.trim()
    if (!name) return
    const existing = types.find((t) => sameName(t.name, name))
    const pending = newTypes.find((t) => sameName(t.name, name))
    onChange((d) => ({
      ...d,
      type: existing
        ? { kind: 'existing', id: existing.id }
        : { kind: 'new', name, category: pending?.category ?? 'strength' },
    }))
    setNaming(false)
    setNewName('')
  }

  const updateExercise = (key: string, change: Partial<DraftExercise>) =>
    onChange((d) => ({ ...d, exercises: d.exercises.map((e) => (e.key === key ? { ...e, ...change } : e)) }))

  return (
    <article className="card day-editor">
      <div className="day-editor-row">
        <select
          className="text-input"
          aria-label="Día de la semana"
          value={day.weekday}
          onChange={(e) => onChange((d) => ({ ...d, weekday: Number(e.target.value) }))}
        >
          {WEEKDAYS.map((name, i) => (
            <option key={name} value={i}>
              {name}
            </option>
          ))}
        </select>
        <label className="minutes-field">
          <input
            className="text-input"
            inputMode="numeric"
            aria-label="Minutos"
            value={day.minutes}
            onChange={(e) => onChange((d) => ({ ...d, minutes: e.target.value }))}
          />
          <span className="muted small">min</span>
        </label>
      </div>

      <select
        className="text-input"
        aria-label="Tipo de entrenamiento"
        value={naming ? OTHER : typeValue}
        onChange={(e) => chooseType(e.target.value)}
      >
        {newTypes.length > 0 && (
          <optgroup label="Nuevos">
            {newTypes.map((t) => (
              <option key={t.name} value={`n:${t.name.toLowerCase()}`}>
                {t.name} (nuevo)
              </option>
            ))}
          </optgroup>
        )}
        {types.length > 0 && (
          <optgroup label="Tus tipos">
            {types.map((t) => (
              <option key={t.id} value={`t:${t.id}`}>
                {t.name}
              </option>
            ))}
          </optgroup>
        )}
        <option value={OTHER}>Otro tipo nuevo…</option>
      </select>

      {naming && (
        <div className="day-editor-row">
          <input
            className="text-input"
            placeholder="Nombre, p. ej. Tren inferior"
            aria-label="Nombre del tipo nuevo"
            maxLength={60}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            autoFocus
          />
          <button type="button" className="button button-small" onClick={addNewType} disabled={!newName.trim()}>
            Usar
          </button>
        </div>
      )}

      <div className="exercise-list">
        <p className="field-label">Ejercicios</p>
        {day.exercises.map((exercise) => (
          <div key={exercise.key} className="exercise-editor">
            <div className="day-editor-row">
              <ExerciseNameInput
                name={exercise.name}
                catalogId={exercise.catalogId ?? null}
                onChange={(name, catalogId) => updateExercise(exercise.key, { name, catalogId })}
              />
              <button
                type="button"
                className="link-button danger"
                aria-label={`Quitar ${exercise.name || 'ejercicio'}`}
                onClick={() => onChange((d) => ({ ...d, exercises: d.exercises.filter((e) => e.key !== exercise.key) }))}
              >
                ✕
              </button>
            </div>
            <div className="exercise-numbers">
              <label>
                <span className="muted small">Series</span>
                <input
                  className="text-input"
                  inputMode="numeric"
                  value={exercise.sets}
                  onChange={(e) => updateExercise(exercise.key, { sets: e.target.value })}
                />
              </label>
              <label>
                <span className="muted small">Reps</span>
                <input
                  className="text-input"
                  placeholder="10-12"
                  maxLength={40}
                  value={exercise.reps}
                  onChange={(e) => updateExercise(exercise.key, { reps: e.target.value })}
                />
              </label>
            </div>
          </div>
        ))}
        <button
          type="button"
          className="link-button add-link"
          onClick={() => onChange((d) => ({ ...d, exercises: [...d.exercises, emptyExercise()] }))}
        >
          + Añadir ejercicio
        </button>
      </div>

      <label className="note-field">
        <span className="field-label">Nota</span>
        <textarea
          className="text-input"
          rows={2}
          maxLength={500}
          value={day.note}
          onChange={(e) => onChange((d) => ({ ...d, note: e.target.value }))}
        />
      </label>

      <button type="button" className="link-button danger remove-day" onClick={onRemove}>
        Quitar este día
      </button>
    </article>
  )
}
