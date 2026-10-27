import { request } from './client.ts'
import type { CatalogExercise, ExerciseDetail, MuscleOption, MuscleSuggestion } from './types.ts'

export const fetchMuscles = () => request<MuscleOption[]>('/api/muscles')

export const fetchTypeExercises = (typeId: number, day: string) =>
  request<MuscleSuggestion[]>(`/api/workout-types/${typeId}/exercises?day=${day}`)

export const searchExercises = (query: string) =>
  request<CatalogExercise[]>(`/api/exercises?q=${encodeURIComponent(query)}`)

export const fetchExercise = (id: number) => request<ExerciseDetail>(`/api/exercises/${id}`)
