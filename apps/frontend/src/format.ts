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

export function average(values: number[]): number | null {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null
}
