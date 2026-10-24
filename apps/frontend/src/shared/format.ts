const dayFormat = new Intl.DateTimeFormat('es-ES', {
  weekday: 'long',
  day: 'numeric',
  month: 'short',
})

const timeFormat = new Intl.DateTimeFormat('es-ES', {
  hour: '2-digit',
  minute: '2-digit',
})

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1)

/** "Jueves, 15 oct" */
export const formatDay = (iso: string) => capitalize(dayFormat.format(new Date(iso)))

/** "14:27" */
export const formatTime = (iso: string) => timeFormat.format(new Date(iso))

/** 1773 -> "29:33" */
export function formatClock(seconds: number): string {
  const total = Math.round(seconds)
  const minutes = Math.floor(total / 60)
  const secs = total % 60
  return `${minutes}:${String(secs).padStart(2, '0')}`
}

/** 1773 -> "29 min" */
export const formatMinutes = (seconds: number) => `${Math.round(seconds / 60)} min`

const shortDateFormat = new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short' })

/** "15 oct" */
export const formatShortDate = (iso: string) => shortDateFormat.format(new Date(iso))

/** 6.4 -> "↓6": how much the HR dropped during a rest (never negative). */
export const formatDrop = (bpm: number) => `↓${Math.round(bpm)}`

/** 3.4 -> "+3", -0.2 -> "0" (sign always shown for non-zero values) */
export function formatSigned(value: number): string {
  const rounded = Math.round(value)
  return rounded > 0 ? `+${rounded}` : rounded < 0 ? `−${Math.abs(rounded)}` : '0'
}

/** A Date as "2026-10-24" in local time, like the dates the API sends. */
export function localIsoDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** Today as "2026-10-24". */
export const todayIso = () => localIsoDate(new Date())

/** The Monday of that date's week, at midnight. */
export function mondayOf(date: Date): Date {
  const monday = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7))
  return monday
}

/** "2026-10-24" -> that day at local midnight. */
export function parseIsoDate(iso: string): Date {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day)
}

/** "Esta semana", "Semana pasada" or "Semana del 12 oct". */
export function weekLabel(monday: Date): string {
  const weeksAgo = Math.round((mondayOf(new Date()).getTime() - monday.getTime()) / (7 * 86_400_000))
  if (weeksAgo === 0) return 'Esta semana'
  if (weeksAgo === 1) return 'Semana pasada'
  return `Semana del ${formatShortDate(monday.toISOString())}`
}
