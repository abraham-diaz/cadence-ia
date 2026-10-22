import type { Category, Exercise, Plan, PlanInput, PlanProposal } from '../../api/types.ts'
import { WEEKDAYS, weekLetter } from './weeks.ts'

// The plan being reviewed, before it is saved. Inputs hold text, as typed.
export type TypeChoice = { kind: 'existing'; id: number } | { kind: 'new'; name: string; category: Category }

export interface DraftExercise {
  key: string
  name: string
  sets: string
  reps: string
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

export const emptyExercise = (): DraftExercise => ({ key: newKey(), name: '', sets: '', reps: '' })

const draftExercises = (exercises: Exercise[]): DraftExercise[] =>
  exercises.map((e) => ({ key: newKey(), name: e.name, sets: e.sets === null ? '' : String(e.sets), reps: e.reps ?? '' }))

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
      type: day.workout_type ? { kind: 'existing', id: day.workout_type.id } : { kind: 'new', name: '', category: 'strength' },
      minutes: String(day.minutes),
      note: day.note ?? '',
      exercises: draftExercises(day.exercises),
    })),
  }
}

/** The new types the plan would create, once per name (case doesn't matter). */
export function newTypes(draft: PlanDraft): { name: string; category: Category }[] {
  const seen = new Map<string, { name: string; category: Category }>()
  for (const day of draft.days) {
    if (day.type.kind === 'new' && day.type.name.trim()) {
      const key = day.type.name.trim().toLowerCase()
      if (!seen.has(key)) seen.set(key, { name: day.type.name.trim(), category: day.type.category })
    }
  }
  return [...seen.values()]
}

export const sameName = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase()

// The same limits as the backend (api/schemas.py).
const MAX = { title: 80, typeName: 60, note: 500, exercise: 80, reps: 40, exercises: 30 }

/** The request body, or the first problem found, in Spanish. */
export function toInput(draft: PlanDraft): PlanInput | string {
  if (!draft.title.trim()) return 'Ponle un nombre al plan'
  if (draft.title.trim().length > MAX.title) return `El nombre del plan pasa de ${MAX.title} caracteres`
  if (!draft.days.length) return 'El plan no tiene ningún día de entrenamiento'

  const days: PlanInput['days'] = []
  for (const day of draft.days) {
    const where = `${WEEKDAYS[day.weekday]}${draft.weeks > 1 ? ` (semana ${weekLetter(day.week)})` : ''}`
    const minutes = Number(day.minutes)
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 600) {
      return `${where}: los minutos deben ser un número entre 1 y 600`
    }
    if (day.type.kind === 'new' && !day.type.name.trim()) return `${where}: el tipo nuevo no tiene nombre`
    if (day.type.kind === 'new' && day.type.name.trim().length > MAX.typeName) {
      return `${where}: el nombre del tipo pasa de ${MAX.typeName} caracteres`
    }
    if (day.note.trim().length > MAX.note) return `${where}: la nota pasa de ${MAX.note} caracteres`

    const exercises = []
    for (const e of day.exercises) {
      const name = e.name.trim()
      if (!name) continue
      if (name.length > MAX.exercise) return `${where}: «${name.slice(0, 30)}…» pasa de ${MAX.exercise} caracteres`
      const sets = e.sets.trim() ? Number(e.sets) : null
      if (sets !== null && (!Number.isInteger(sets) || sets < 1 || sets > 20)) {
        return `${where}: las series de «${name}» deben ser un número entre 1 y 20`
      }
      if (e.reps.trim().length > MAX.reps) {
        return `${where}: las repeticiones de «${name}» pasan de ${MAX.reps} caracteres`
      }
      exercises.push({ name, sets, reps: e.reps.trim() || null })
    }
    if (exercises.length > MAX.exercises) return `${where}: más de ${MAX.exercises} ejercicios`

    days.push({
      week: day.week,
      weekday: day.weekday,
      ...(day.type.kind === 'existing'
        ? { workout_type_id: day.type.id }
        : { new_type: { name: day.type.name.trim(), category: day.type.category } }),
      minutes,
      note: day.note.trim() || null,
      exercises,
    })
  }
  return { title: draft.title.trim(), weeks: draft.weeks, current_week: draft.currentWeek, days }
}

// Kept on the phone so iOS closing the app doesn't lose the review.
const KEY = 'cadence:plan-draft'

export function loadDraft(): PlanDraft | null {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) ?? 'null')
    return saved && Array.isArray(saved.days) ? saved : null
  } catch {
    return null
  }
}

export function saveDraft(draft: PlanDraft | null) {
  try {
    if (draft) localStorage.setItem(KEY, JSON.stringify(draft))
    else localStorage.removeItem(KEY)
  } catch {
    // Private mode or storage full: the review still works until the app is closed.
  }
}
