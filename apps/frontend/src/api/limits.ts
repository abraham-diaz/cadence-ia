// The same limits the backend validates (api/schemas/), so forms stop the user before a 422.
export const LIMITS = {
  typeName: 60,
  planTitle: 80,
  planWeeks: 4,
  minutes: 600,
  note: 500,
  exercisesPerDay: 30,
  exerciseName: 80,
  sets: 20,
  reps: 40,
  chatMessage: 4000,
} as const
