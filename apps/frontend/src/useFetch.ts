import { useEffect, useState } from 'react'

type State<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ok'; data: T }

/** Run `load` once per `key` and track loading / error / data. */
export function useFetch<T>(load: () => Promise<T>, key: string): State<T> {
  const [state, setState] = useState<State<T>>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    load()
      .then((data) => !cancelled && setState({ status: 'ok', data }))
      .catch((err: Error) => !cancelled && setState({ status: 'error', error: err.message }))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return state
}
