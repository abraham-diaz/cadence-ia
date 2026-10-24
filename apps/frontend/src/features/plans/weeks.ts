import type { PlanDay } from '../../api/types.ts'

export const WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

/** 0 -> "A", 1 -> "B"... */
export const weekLetter = (week: number) => String.fromCharCode(65 + week)

/** Monday = 0, like the backend. */
export const todayWeekday = () => (new Date().getDay() + 6) % 7

/** "Tren superior · 35 min" */
export const describeDay = (day: PlanDay) => `${day.workout_type?.name ?? 'Sin tipo'} · ${day.minutes} min`
