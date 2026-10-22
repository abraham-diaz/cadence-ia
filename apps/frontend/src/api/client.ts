import type { ErrorCode } from './types.ts'

// What the user reads for each error the API can return. `null` shows the
// server's own message, already written for the user (e.g. Gemini's quota).
// Typed against the backend: a new error code won't compile until it's here.
const ERROR_MESSAGES: Record<ErrorCode, string | null> = {
  session_not_found: 'No encontrado',
  workout_type_not_found: 'Ese tipo de entrenamiento ya no existe',
  duplicate_workout_type: 'Ya existe un tipo con ese nombre',
  session_without_type: 'Elige antes el tipo de entrenamiento',
  assessment_unavailable: null,
}

async function errorMessage(response: Response): Promise<string> {
  const body = await response.json().catch(() => null)
  const detail = typeof body?.detail === 'string' ? body.detail : null
  const code = body?.code as ErrorCode | undefined
  if (code && code in ERROR_MESSAGES) return ERROR_MESSAGES[code] ?? detail ?? `Error ${response.status}`
  if (response.status === 404) return 'No encontrado'
  return detail ?? `Error ${response.status}`
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  return (response.status === 204 ? undefined : await response.json()) as T
}

export const send = <T>(method: string, path: string, body?: unknown) =>
  request<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) })
