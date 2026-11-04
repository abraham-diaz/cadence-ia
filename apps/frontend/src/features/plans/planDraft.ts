import { LIMITS } from '../../api/limits.ts'
import type { Category, Exercise, Plan, PlanInput, PlanProposal } from '../../api/types.ts'
import { loadJson, saveJson } from '../../shared/storage.ts'
import { WEEKDAYS, weekLetter } from './weeks.ts'

// The plan being reviewed, before it is saved. Inputs hold text, as typed.
export interface NewTypeDraft {
  name: string
  category: Category
}

export type TypeChoice = { kind: 'existing'; id: number } | ({ kind: 'new' } & NewTypeDraft)

export interface DraftExercise {
  key: string
  name: string
  sets: string
  reps: string
  catalogId?: number | null // picked from the catalog; older drafts don't have it
}

export interface DraftDay {
  key: string
  week: number
  weekday: number
  type: TypeChoice
  minutes: string
  note: string
  exercises: DraftExercise[]
}

export interface PlanDraft {
  // 'plan': editing the saved plan. Drafts saved before this existed have none: they came from the chat.
  source?: 'chat' | 'plan'
  title: string
  weeks: number
  currentWeek: number
  days: DraftDay[]
}

let counter = 0
// crypto.randomUUID() only exists over HTTPS, and the app is also opened over plain HTTP at home.
export const newKey = () => `k${Date.now().toString(36)}${(counter++).toString(36)}`

export const emptyExercise = (): DraftExercise => ({ key: newKey(), name: '', sets: '', reps: '', catalogId: null })

const draftExercises = (exercises: Exercise[]): DraftExercise[] =>
  exercises.map((e) => ({
    key: newKey(),
    name: e.name,
    sets: e.sets === null ? '' : String(e.sets),
    reps: e.reps ?? '',
    catalogId: e.catalog_id,
  }))

export function fromProposal(proposal: PlanProposal): PlanDraft {
  return {
    source: 'chat',
    title: proposal.title,
    weeks: proposal.weeks,
    currentWeek: 0,
    days: proposal.days.map((day) => ({
      key: newKey(),
      week: day.week,
      weekday: day.weekday,
      type:
        day.workout_type_id !== null
          ? { kind: 'existing', id: day.workout_type_id }
          : { kind: 'new', name: day.type_name, category: day.category },
      minutes: String(day.minutes),
      note: day.note ?? '',
      exercises: draftExercises(day.exercises),
    })),
  }
}

/** The saved plan, ready to edit. Saving it again keeps the same A/B cycle. */
export function fromPlan(plan: Plan): PlanDraft {
  return {
    source: 'plan',
    title: plan.title,
    weeks: plan.weeks,
    currentWeek: plan.current_week,
    days: plan.days.map((day) => ({
      key: newKey(),
      week: day.week,
      weekday: day.weekday,
      // A deleted type leaves the day without one: the review asks for a name.
      type: day.workout_type
        ? { kind: 'existing', id: day.workout_type.id }
        : { kind: 'new', name: '', category: 'strength' },
      minutes: String(day.minutes),
      note: day.note ?? '',
      exercises: draftExercises(day.exercises),
    })),
  }
}

/** The new types the plan would create, once per name (case doesn't matter). */
export function newTypes(draft: PlanDraft): NewTypeDraft[] {
  const seen = new Map<string, NewTypeDraft>()
  for (const day of draft.days) {
    if (day.type.kind === 'new' && day.type.name.trim()) {
      const key = day.type.name.trim().toLowerCase()
      if (!seen.has(key)) seen.set(key, { name: day.type.name.trim(), category: day.type.category })
    }
  }
  return [...seen.values()]
}

export const sameName = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase()

/** The request body, or the first problem found, in Spanish. */
export function toInput(draft: PlanDraft): PlanInput | string {
  if (!draft.title.trim()) return 'Ponle un nombre al plan'
  if (draft.title.trim().length > LIMITS.planTitle) return `El nombre del plan pasa de ${LIMITS.planTitle} caracteres`
  if (!draft.days.length) return 'El plan no tiene ningún día de entrenamiento'

  const days: PlanInput['days'] = []
  for (const day of draft.days) {
    const where = `${WEEKDAYS[day.weekday]}${draft.weeks > 1 ? ` (semana ${weekLetter(day.week)})` : ''}`
    const minutes = Number(day.minutes)
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > LIMITS.minutes) {
      return `${where}: los minutos deben ser un número entre 1 y ${LIMITS.minutes}`
    }
    if (day.type.kind === 'new' && !day.type.name.trim()) return `${where}: el tipo nuevo no tiene nombre`
    if (day.type.kind === 'new' && day.type.name.trim().length > LIMITS.typeName) {
      return `${where}: el nombre del tipo pasa de ${LIMITS.typeName} caracteres`
    }
    if (day.note.trim().length > LIMITS.note) return `${where}: la nota pasa de ${LIMITS.note} caracteres`

    const exercises = []
    for (const e of day.exercises) {
      const name = e.name.trim()
      if (!name) continue
      if (name.length > LIMITS.exerciseName) {
        return `${where}: «${name.slice(0, 30)}…» pasa de ${LIMITS.exerciseName} caracteres`
      }
      const sets = e.sets.trim() ? Number(e.sets) : null
      if (sets !== null && (!Number.isInteger(sets) || sets < 1 || sets > LIMITS.sets)) {
        return `${where}: las series de «${name}» deben ser un número entre 1 y ${LIMITS.sets}`
      }
      if (e.reps.trim().length > LIMITS.reps) {
        return `${where}: las repeticiones de «${name}» pasan de ${LIMITS.reps} caracteres`
      }
      exercises.push({ name, sets, reps: e.reps.trim() || null, catalog_id: e.catalogId ?? null })
    }
    if (exercises.length > LIMITS.exercisesPerDay) return `${where}: más de ${LIMITS.exercisesPerDay} ejercicios`

    days.push({
      week: day.week,
      weekday: day.weekday,
      ...(day.type.kind === 'existing'
        ? { workout_type_id: day.type.id }
        : { new_type: { name: day.type.name.trim(), category: day.type.category, muscles: [] } }),
      minutes,
      note: day.note.trim() || null,
      exercises,
    })
  }
  return { title: draft.title.trim(), weeks: draft.weeks, current_week: draft.currentWeek, days }
}

const KEY = 'cadence:plan-draft'

export const loadDraft = () =>
  loadJson<PlanDraft | null>(KEY, null, (saved) => Array.isArray((saved as PlanDraft | null)?.days))

export const saveDraft = (draft: PlanDraft | null) => saveJson(KEY, draft)
