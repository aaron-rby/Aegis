import { useEffect, useState } from 'react'

export function relativeTime(value, now = Date.now()) {
  if (!value) return 'No upload yet'
  const time = new Date(value).getTime()
  if (!Number.isFinite(time)) return 'Unknown time'
  const seconds = Math.max(0, Math.floor((now - time) / 1000))
  if (seconds < 10) return 'Just now'
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hr ago`
  const days = Math.floor(hours / 24)
  return `${days} day${days === 1 ? '' : 's'} ago`
}

export function useRelativeTime(value) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30_000)
    return () => window.clearInterval(timer)
  }, [])
  return relativeTime(value, now)
}
