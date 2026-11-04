// Kept on the phone: iOS kills home-screen apps in the background, losing what was in memory.

/** The saved value, or `fallback` if there's none or it isn't valid. */
export function loadJson<T>(key: string, fallback: T, isValid: (value: unknown) => boolean): T {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(key) ?? 'null')
    return isValid(saved) ? (saved as T) : fallback
  } catch {
    return fallback
  }
}

/** `null` removes it. */
export function saveJson(key: string, value: unknown) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Private mode or storage full: everything still works until the app is closed.
  }
}
