import { useEffect, useState } from 'react'

export function useCountUp(value) {
  const [display, setDisplay] = useState(value)
  useEffect(() => {
    if (typeof value !== 'number') { setDisplay(value); return }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setDisplay(value); return }
    if (typeof display !== 'number') { setDisplay(value); return }
    const from = display
    if (from === value) return
    const start = performance.now()
    let frame
    const tick = now => {
      const progress = Math.min(1, (now - start) / 600)
      setDisplay(Math.round(from + (value - from) * (1 - Math.pow(1 - progress, 3))))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  // The animation intentionally starts from the value displayed before this update.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])
  return display
}
