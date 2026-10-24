import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../services/api'

/** Fetches on mount and whenever `deps` change; optionally polls. */
export function useApi<T>(fn: () => Promise<T>, deps: unknown[] = [], pollMs = 0) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const fnRef = useRef(fn)
  fnRef.current = fn

  const load = useCallback(async () => {
    try {
      setData(await fnRef.current())
      setError(null)
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError('unknown', String(e)))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    if (!pollMs) return
    const id = window.setInterval(() => void load(), pollMs)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, pollMs, load])

  return { data, error, loading, reload: load }
}
