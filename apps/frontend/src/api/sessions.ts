import { request, send } from './client.ts'
import type { Assessment, SessionDetail, SessionSummary } from './types.ts'

const sessionPath = (id: string) => `/api/sessions/${encodeURIComponent(id)}`

export const fetchSessions = () => request<SessionSummary[]>('/api/sessions')

export const fetchSession = (id: string) => request<SessionDetail>(sessionPath(id))

export const setSessionType = (id: string, workoutTypeId: number | null) =>
  send<SessionDetail>('PUT', `${sessionPath(id)}/workout-type`, { workout_type_id: workoutTypeId })

export const requestAssessment = (id: string) =>
  send<Assessment>('POST', `${sessionPath(id)}/assessment`)
