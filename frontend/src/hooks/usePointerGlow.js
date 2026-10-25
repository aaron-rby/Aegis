import { useEffect, useRef } from 'react'

export function usePointerGlow() {
  const frame = useRef(0)
  useEffect(() => () => cancelAnimationFrame(frame.current), [])
  function onPointerMove(event) {
    if (event.pointerType === 'touch' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const element = event.currentTarget
    const bounds = element.getBoundingClientRect()
    const x = event.clientX - bounds.left
    const y = event.clientY - bounds.top
    cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(() => {
      element.style.setProperty('--mx', `${x}px`)
      element.style.setProperty('--my', `${y}px`)
      element.style.setProperty('--rx', `${((y / bounds.height) - .5) * -8}deg`)
      element.style.setProperty('--ry', `${((x / bounds.width) - .5) * 8}deg`)
    })
  }
  function onPointerLeave(event) {
    cancelAnimationFrame(frame.current)
    event.currentTarget.style.setProperty('--rx', '0deg')
    event.currentTarget.style.setProperty('--ry', '0deg')
  }
  return { onPointerMove, onPointerLeave }
}
