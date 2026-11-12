import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Calls `load` now and every `intervalMs` while the tab is visible, so the
 * dashboard picks up calls that finish while it's open.
 */
export function usePolling(load, intervalMs = 10000) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const loadRef = useRef(load)

  useEffect(() => {
    loadRef.current = load
  }, [load])

  const refresh = useCallback(async () => {
    try {
      setData(await loadRef.current())
      setError(null)
      setUpdatedAt(new Date())
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    // Kick off the first load asynchronously so no state is set during the effect itself.
    const first = setTimeout(refresh, 0)
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') refresh()
    }, intervalMs)
    return () => {
      clearTimeout(first)
      clearInterval(timer)
    }
  }, [refresh, intervalMs])

  return { data, error, updatedAt, refresh }
}
