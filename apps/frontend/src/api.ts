export interface SessionSummary {
  id: string
  start_time: string
  sport: string
  duration_s: number
  calories: number
  hr_min: number
  hr_avg: number
  hr_max: number
  sets: number
  rests: number
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

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(response.status === 404 ? 'No encontrado' : `Error ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const fetchSessions = () => getJson<SessionSummary[]>('/api/sessions')

export const fetchSession = (id: string) =>
  getJson<SessionDetail>(`/api/sessions/${encodeURIComponent(id)}`)
