import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { savePlan } from '../../api/plans.ts'
import type { Category } from '../../api/types.ts'
import { fetchWorkoutTypes } from '../../api/workoutTypes.ts'
import { useFetch } from '../../shared/useFetch.ts'
import { CATEGORY_LABELS } from '../workout-types/categories.ts'
import DayEditor from './DayEditor.tsx'
import { loadDraft, newKey, newTypes, sameName, saveDraft, toInput, type DraftDay, type PlanDraft } from './planDraft.ts'
import './plans.css'
import { weekLetter } from './weeks.ts'

const MAX_WEEKS = 4

export default function PlanReviewPage() {
  const navigate = useNavigate()
  const [draft, setDraft] = useState<PlanDraft | null>(loadDraft)
  const { state: typesState } = useFetch(fetchWorkoutTypes, 'types')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [viewWeek, setViewWeek] = useState(() => loadDraft()?.currentWeek ?? 0)

  useEffect(() => saveDraft(draft), [draft])

  if (!draft) {
    return (
      <main className="page">
        <nav className="top-bar">
          <Link to="/plan/nuevo" className="back-link">
            ‹ Chat
          </Link>
        </nav>
        <p className="notice">No hay ningún plan por revisar. Pulsa «Usar este plan» en el chat.</p>
      </main>
    )
  }

  const types = typesState.status === 'ok' ? typesState.data : []
  const pendingTypes = newTypes(draft)

  const update = (change: (d: PlanDraft) => PlanDraft) => setDraft((d) => d && change(d))
  const updateDay = (key: string, change: (day: DraftDay) => DraftDay) =>
    update((d) => ({ ...d, days: d.days.map((day) => (day.key === key ? change(day) : day)) }))

  // Applies to every day using that new type.
  const updateNewType = (name: string, change: (day: DraftDay) => DraftDay) =>
    update((d) => ({
      ...d,
      days: d.days.map((day) => (day.type.kind === 'new' && sameName(day.type.name, name) ? change(day) : day)),
    }))

  function addDay(week: number) {
    const type = types[0] ? ({ kind: 'existing', id: types[0].id } as const) : null
    const day: DraftDay = {
      key: newKey(),
      week,
      weekday: 0,
      type: type ?? { kind: 'new', name: 'Entrenamiento', category: 'strength' },
      minutes: '30',
      note: '',
      exercises: [],
    }
    update((d) => ({ ...d, days: [...d.days, day] }))
  }

  function removeWeek(week: number) {
    if (!window.confirm(`¿Quitar la semana ${weekLetter(week)} y sus días?`)) return
    update((d) => ({
      ...d,
      weeks: d.weeks - 1,
      currentWeek: Math.min(d.currentWeek, d.weeks - 2),
      days: d.days.filter((day) => day.week !== week).map((day) => (day.week > week ? { ...day, week: day.week - 1 } : day)),
    }))
    setViewWeek(Math.max(0, week - 1))
  }

  const editing = draft.source === 'plan'

  function discard() {
    const question = editing
      ? '¿Descartar los cambios? Tu plan se queda como estaba.'
      : '¿Descartar este plan? La conversación del chat se mantiene.'
    if (!window.confirm(question)) return
    saveDraft(null)
    navigate(editing ? '/plan' : '/plan/nuevo')
  }

  async function save() {
    if (!draft) return
    const input = toInput(draft)
    if (typeof input === 'string') {
      setError(input)
      return
    }
    setSaving(true)
    setError(null)
    try {
      await savePlan(input)
      saveDraft(null)
      navigate('/plan', { replace: true })
    } catch (err) {
      setError((err as Error).message)
      setSaving(false)
    }
  }

  const weeks = Array.from({ length: draft.weeks }, (_, i) => i)
  const week = Math.min(viewWeek, draft.weeks - 1)

  function addWeek() {
    update((d) => ({ ...d, weeks: d.weeks + 1 }))
    setViewWeek(draft?.weeks ?? 0)
  }

  return (
    <main className="page review-page">
      <nav className="top-bar chat-top-bar">
        <Link to={editing ? '/plan' : '/plan/nuevo'} className="back-link">
          {editing ? '‹ Plan' : '‹ Chat'}
        </Link>
        <button type="button" className="link-button danger" onClick={discard}>
          {editing ? 'Descartar cambios' : 'Descartar'}
        </button>
      </nav>

      <header className="page-header">
        <p className="eyebrow">Plan</p>
        <h1>{editing ? 'Editar plan' : 'Revisar plan'}</h1>
      </header>

      <label className="review-field">
        <span className="field-label">Nombre</span>
        <input
          className="text-input"
          maxLength={80}
          value={draft.title}
          onChange={(e) => update((d) => ({ ...d, title: e.target.value }))}
        />
      </label>

      {pendingTypes.length > 0 && (
        <section className="card new-types">
          <h2 className="section-title">Tipos nuevos</h2>
          <p className="muted small">Se crearán al guardar. Puedes usar uno de los tuyos en su lugar.</p>
          {pendingTypes.map((type) => (
            <div key={type.name} className="new-type-row">
              <p className="type-name">{type.name}</p>
              <select
                className="text-input"
                aria-label={`Qué hacer con ${type.name}`}
                value="new"
                onChange={(e) =>
                  updateNewType(type.name, (day) => ({ ...day, type: { kind: 'existing', id: Number(e.target.value) } }))
                }
              >
                <option value="new">Crear como tipo nuevo</option>
                {types.map((t) => (
                  <option key={t.id} value={t.id}>
                    Usar «{t.name}»
                  </option>
                ))}
              </select>
              <div className="segmented" role="radiogroup" aria-label={`Categoría de ${type.name}`}>
                {(Object.keys(CATEGORY_LABELS) as Category[]).map((category) => (
                  <button
                    key={category}
                    type="button"
                    role="radio"
                    aria-checked={type.category === category}
                    className={type.category === category ? 'selected' : ''}
                    onClick={() =>
                      updateNewType(type.name, (day) => ({ ...day, type: { kind: 'new', name: type.name, category } }))
                    }
                  >
                    {CATEGORY_LABELS[category]}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}

      {draft.weeks > 1 && (
        <div
          className="segmented"
          role="tablist"
          aria-label="Semana"
          style={{ gridTemplateColumns: `repeat(${draft.weeks}, 1fr)` }}
        >
          {weeks.map((w) => (
            <button
              key={w}
              type="button"
              role="tab"
              aria-selected={week === w}
              className={week === w ? 'selected' : ''}
              onClick={() => setViewWeek(w)}
            >
              Semana {weekLetter(w)}
            </button>
          ))}
        </div>
      )}

      <section className="review-week" role={draft.weeks > 1 ? 'tabpanel' : undefined}>
        {draft.weeks > 1 && (
          <div className="review-week-head">
            {draft.currentWeek === week ? (
              <span className="chip">Semana actual</span>
            ) : (
              <button
                type="button"
                className="link-button"
                onClick={() => update((d) => ({ ...d, currentWeek: week }))}
              >
                Marcar como semana actual
              </button>
            )}
            <button type="button" className="link-button danger" onClick={() => removeWeek(week)}>
              Quitar semana
            </button>
          </div>
        )}
        {draft.days
          .filter((day) => day.week === week)
          .sort((a, b) => a.weekday - b.weekday)
          .map((day) => (
            <DayEditor
              key={day.key}
              day={day}
              types={types}
              newTypes={pendingTypes}
              onChange={(change) => updateDay(day.key, change)}
              onRemove={() => update((d) => ({ ...d, days: d.days.filter((x) => x.key !== day.key) }))}
            />
          ))}
        <button type="button" className="button button-secondary" onClick={() => addDay(week)}>
          + Añadir día
        </button>
      </section>

      {draft.weeks < MAX_WEEKS && (
        <button type="button" className="link-button add-link" onClick={addWeek}>
          + Añadir semana {weekLetter(draft.weeks)}
        </button>
      )}

      <div className="review-actions">
        {error && <p className="form-error">{error}</p>}
        <button type="button" className="button" onClick={save} disabled={saving}>
          {saving ? 'Guardando…' : editing ? 'Guardar cambios' : 'Guardar plan'}
        </button>
      </div>
    </main>
  )
}
