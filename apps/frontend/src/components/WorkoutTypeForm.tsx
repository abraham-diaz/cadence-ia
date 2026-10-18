import { useState, type FormEvent } from 'react'
import { CATEGORY_LABELS, type Category, type WorkoutTypeInput } from '../api.ts'

interface Props {
  initial?: WorkoutTypeInput
  submitLabel: string
  onSubmit: (input: WorkoutTypeInput) => Promise<void>
  onCancel?: () => void
}

/** Name + category form, shared by "new type" and "edit type". */
export default function WorkoutTypeForm({ initial, submitLabel, onSubmit, onCancel }: Props) {
  const [name, setName] = useState(initial?.name ?? '')
  const [category, setCategory] = useState<Category>(initial?.category ?? 'strength')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    setSaving(true)
    setError(null)
    try {
      await onSubmit({ name: name.trim(), category })
    } catch (err) {
      setError((err as Error).message)
      setSaving(false)
    }
  }

  return (
    <form className="type-form" onSubmit={handleSubmit}>
      <input
        className="text-input"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Nombre, p. ej. Pierna"
        maxLength={40}
        aria-label="Nombre del tipo"
        autoFocus
      />
      <div className="segmented" role="radiogroup" aria-label="Categoría">
        {(Object.keys(CATEGORY_LABELS) as Category[]).map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={category === value}
            className={category === value ? 'selected' : ''}
            onClick={() => setCategory(value)}
          >
            {CATEGORY_LABELS[value]}
          </button>
        ))}
      </div>
      {error && <p className="form-error">{error}</p>}
      <div className="form-actions">
        {onCancel && (
          <button type="button" className="button button-secondary" onClick={onCancel}>
            Cancelar
          </button>
        )}
        <button type="submit" className="button" disabled={saving || !name.trim()}>
          {submitLabel}
        </button>
      </div>
    </form>
  )
}
