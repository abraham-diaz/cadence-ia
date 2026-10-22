import { request, send } from './client.ts'
import type { WorkoutType, WorkoutTypeInput } from './types.ts'

export const fetchWorkoutTypes = () => request<WorkoutType[]>('/api/workout-types')

export const createWorkoutType = (input: WorkoutTypeInput) =>
  send<WorkoutType>('POST', '/api/workout-types', input)

export const updateWorkoutType = (id: number, input: WorkoutTypeInput) =>
  send<WorkoutType>('PUT', `/api/workout-types/${id}`, input)

export const deleteWorkoutType = (id: number) => send<void>('DELETE', `/api/workout-types/${id}`)
