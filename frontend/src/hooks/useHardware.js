import { useCallback, useEffect, useRef, useState } from 'react'

async function request(path, options = {}) {
  const response = await fetch(path, { cache: 'no-store', ...options })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || `Hardware service returned ${response.status}. Restart the backend console if it predates this update.`)
  return data
}
export function useHardware() {
  const [snapshot, setSnapshot] = useState({ online: false, history: [], serial: {} })
  const [ports, setPorts] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [portsBusy, setPortsBusy] = useState(false)
  const pollRef = useRef(() => {})
  const actionLock = useRef(false)
  useEffect(() => {
    let stopped = false, polling = false
    let current
    async function poll() {
      if (polling || stopped) return
      polling = true
      current = new AbortController()
      const timeout = setTimeout(() => current.abort(), 4000)
      try {
        const next = await request('/api/hardware', { signal: current.signal })
        if (!stopped) setSnapshot({ ...next, fetchedAt: performance.now() })
      } catch (e) {
        if (!stopped) setSnapshot(old => ({ ...old, online: false, fetchError: e.message }))
      } finally { clearTimeout(timeout); polling = false }
    }
    pollRef.current = poll
    poll()
    const timer = setInterval(poll, 1000)
    return () => { stopped = true; clearInterval(timer); current?.abort() }
  }, [])
  const refreshPorts = useCallback(async () => {
    setPortsBusy(true)
    try { const next = await request('/api/serial/ports'); setPorts(next.ports); setError('') }
    catch (e) { setError(e.message) }
    finally { setPortsBusy(false) }
  }, [])
  const action = useCallback(async (kind, payload) => {
    if (actionLock.current) return
    actionLock.current = true; setBusy(true); setError('')
    try {
      await request(`/api/serial/${kind}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload || {}) })
      await pollRef.current()
    } catch (e) { setError(e.message) }
    finally { actionLock.current = false; setBusy(false) }
  }, [])
  const triggerCamera = useCallback(async () => {
    const result = await request('/api/serial/trigger', { method: 'POST' })
    await pollRef.current()
    return result
  }, [])
  const age = snapshot.sample_age_seconds == null ? Infinity : snapshot.sample_age_seconds + (performance.now() - snapshot.fetchedAt) / 1000
  return { snapshot, live: snapshot.online === true && age < 15, ports, error, busy, portsBusy, refreshPorts, action, triggerCamera }
}
