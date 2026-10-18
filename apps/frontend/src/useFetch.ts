import { useCallback, useEffect, useState } from 'react'

export type FetchState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ok'; data: T }

/**
 * Run `load` once per `key` and track loading / error / data.
 * `reload` fetches again; `setData` replaces the data (e.g. with a PUT response).
 */
export function useFetch<T>(load: () => Promise<T>, key: string) {
  const [state, setState] = useState<FetchState<T>>({ status: 'loading' })
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let cancelled = false
    load()
      .then((data) => !cancelled && setState({ status: 'ok', data }))
      .catch((err: Error) => !cancelled && setState({ status: 'error', error: err.message }))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, version])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  const setData = useCallback((data: T) => setState({ status: 'ok', data }), [])

  return { state, reload, setData }
}
