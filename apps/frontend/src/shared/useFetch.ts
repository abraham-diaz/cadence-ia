import { useCallback, useEffect, useState } from 'react'

export type FetchState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ok'; data: T }

// The last data of each key: going back to a page paints it at once, then refreshes it.
const cache = new Map<string, unknown>()

// Refetches when the app returns to the foreground: iOS keeps home-screen apps
// in memory, so new workouts never showed up otherwise.
export function useFetch<T>(load: () => Promise<T>, key: string) {
  const [state, setState] = useState<FetchState<T>>(() =>
    cache.has(key) ? { status: 'ok', data: cache.get(key) as T } : { status: 'loading' },
  )
  const [version, setVersion] = useState(0)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    let cancelled = false
    setRefreshing(true)
    load()
      .then((data) => {
        cache.set(key, data)
        if (cancelled) return
        // Tab pages refetch on every visit: an unchanged answer shouldn't redraw them.
        setState((prev) =>
          prev.status === 'ok' && JSON.stringify(prev.data) === JSON.stringify(data) ? prev : { status: 'ok', data },
        )
      })
      .catch((err: Error) => {
        // A failed refresh (e.g. no signal) keeps showing the data we already have.
        if (!cancelled) setState((prev) => (prev.status === 'ok' ? prev : { status: 'error', error: err.message }))
      })
      .finally(() => !cancelled && setRefreshing(false))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, version])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  const setData = useCallback(
    (data: T) => {
      cache.set(key, data)
      setState({ status: 'ok', data })
    },
    [key],
  )

  useEffect(() => {
    const onVisible = () => document.visibilityState === 'visible' && reload()
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [reload])

  return { state, reload, setData, refreshing }
}
