import { useCallback, useEffect, useState } from 'react'

export type FetchState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ok'; data: T }

/**
 * Run `load` once per `key` and track loading / error / data.
 * `reload` fetches again; `setData` replaces the data (e.g. with a PUT response).
 *
 * It also fetches again whenever the app comes back to the foreground: iOS
 * keeps home-screen apps in memory, so without this the list never showed
 * workouts that arrived while the app was in the background.
 */
export function useFetch<T>(load: () => Promise<T>, key: string) {
  const [state, setState] = useState<FetchState<T>>({ status: 'loading' })
  const [version, setVersion] = useState(0)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    let cancelled = false
    setRefreshing(true)
    load()
      .then((data) => !cancelled && setState({ status: 'ok', data }))
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
  const setData = useCallback((data: T) => setState({ status: 'ok', data }), [])

  useEffect(() => {
    const onVisible = () => document.visibilityState === 'visible' && reload()
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [reload])

  return { state, reload, setData, refreshing }
}
