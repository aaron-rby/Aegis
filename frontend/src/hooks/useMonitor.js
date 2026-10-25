import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../services/api.js'
async function archive(signal) {
  const first = await api.photos({ perPage: 100 }, signal)
  const remaining = await Promise.all(Array.from({ length: Math.max(0, first.pages - 1) }, (_, i) => api.photos({ page: i + 2, perPage: 100 }, signal)))
  return [...new Map([first, ...remaining].flatMap(page => page.items).map(photo => [photo.id, photo])).values()]
}
export function useMonitor() {
  const [data, setData] = useState({ photos: [], status: null, loading: true, offline: false, archiveError: false, updatedAt: null })
  const [refreshing, setRefreshing] = useState(false)
  const refreshRef = useRef(() => {})
  useEffect(() => {
    const controller = new AbortController()
    let busy = false
    async function refresh(manual = false) {
      if (busy || controller.signal.aborted || (!manual && document.hidden)) return
      busy = true
      if (manual) setRefreshing(true)
      try {
        const [status, photos] = await Promise.allSettled([api.status(controller.signal), archive(controller.signal)])
        if (controller.signal.aborted) return
        setData(previous => ({ photos: photos.status === 'fulfilled' ? photos.value : previous.photos,
          status: status.status === 'fulfilled' ? status.value : previous.status,
          loading: false, offline: status.status !== 'fulfilled', archiveError: photos.status !== 'fulfilled',
          updatedAt: status.status === 'fulfilled' && photos.status === 'fulfilled' ? new Date().toISOString() : previous.updatedAt }))
      } finally { busy = false; if (!controller.signal.aborted) setRefreshing(false) }
    }
    refreshRef.current = () => refresh(true)
    refresh(true)
    const timer = setInterval(refresh, 2000)
    const visible = () => { if (!document.hidden) refresh() }
    document.addEventListener('visibilitychange', visible)
    return () => { controller.abort(); clearInterval(timer); document.removeEventListener('visibilitychange', visible) }
  }, [])
  const refresh = useCallback(() => refreshRef.current(), [])
  return { ...data, refreshing, refresh }
}
