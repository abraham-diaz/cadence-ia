export type Category = 'strength' | 'cardio'

export const CATEGORY_LABELS: Record<Category, string> = {
  strength: 'Fuerza',
  cardio: 'Cardio',
}

export interface WorkoutTypeRef {
  id: number
  name: string
  category: Category
}

export interface WorkoutType extends WorkoutTypeRef {
  session_count: number
}

export interface SessionSummary {
  id: string
  start_time: string
  sport: string
  duration_s: number
  calories: number
  hr_min: number
  hr_avg: number
  hr_max: number
  workout_type: WorkoutTypeRef | null
  sets: number | null
  rests: number | null
}

export interface Segment {
  kind: 'work' | 'rest'
  start_s: number
  end_s: number
  duration_s: number
  hr_start: number
  hr_end: number
  hr_avg: number
  drop_30s: number | null
  drop_60s: number | null
}

export interface HeartRatePoint {
  t: number
  hr: number
}

export interface SessionDetail extends SessionSummary {
  device: string | null
  threshold_bpm: number
  segments: Segment[]
  heart_rate: HeartRatePoint[]
}

export interface WorkoutTypeInput {
  name: string
  category: Category
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
  })
  if (!response.ok) {
    if (response.status === 404) throw new Error('No encontrado')
    if (response.status === 409) throw new Error('Ya existe un tipo con ese nombre')
    throw new Error(`Error ${response.status}`)
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}

const send = <T>(method: string, path: string, body?: unknown) =>
  request<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) })

export const fetchSessions = () => request<SessionSummary[]>('/api/sessions')

export const fetchSession = (id: string) =>
  request<SessionDetail>(`/api/sessions/${encodeURIComponent(id)}`)

export const setSessionType = (id: string, workoutTypeId: number | null) =>
  send<SessionDetail>('PUT', `/api/sessions/${encodeURIComponent(id)}/workout-type`, {
    workout_type_id: workoutTypeId,
  })

export const fetchWorkoutTypes = () => request<WorkoutType[]>('/api/workout-types')

export const createWorkoutType = (input: WorkoutTypeInput) =>
  send<WorkoutType>('POST', '/api/workout-types', input)

export const updateWorkoutType = (id: number, input: WorkoutTypeInput) =>
  send<WorkoutType>('PUT', `/api/workout-types/${id}`, input)

export const deleteWorkoutType = (id: number) => send<void>('DELETE', `/api/workout-types/${id}`)
