import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router'

export const TAB_PATHS = ['/', '/plan', '/tipos']

const MIN_DISTANCE = 60

/** Swiping left or right moves to the next or previous tab. */
export function useTabSwipe() {
  const { pathname } = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    let start: { x: number; y: number } | null = null

    function onStart(e: TouchEvent) {
      const ignored = e.touches.length > 1 || (e.target instanceof Element && hasOwnGesture(e.target))
      start = ignored ? null : { x: e.touches[0].clientX, y: e.touches[0].clientY }
    }

    function onEnd(e: TouchEvent) {
      if (!start) return
      const touch = e.changedTouches[0]
      const dx = touch.clientX - start.x
      const dy = touch.clientY - start.y
      start = null
      if (Math.abs(dx) < MIN_DISTANCE || Math.abs(dx) < 2 * Math.abs(dy)) return

      const current = TAB_PATHS.indexOf(pathname)
      if (current === -1) return // a detail page: the swipe is iOS's "back"
      const to = TAB_PATHS[current + (dx < 0 ? 1 : -1)]
      if (!to) return
      navigate(to)
    }

    function onCancel() {
      start = null
    }

    window.addEventListener('touchstart', onStart, { passive: true })
    window.addEventListener('touchend', onEnd, { passive: true })
    window.addEventListener('touchcancel', onCancel, { passive: true })
    return () => {
      window.removeEventListener('touchstart', onStart)
      window.removeEventListener('touchend', onEnd)
      window.removeEventListener('touchcancel', onCancel)
    }
  }, [pathname, navigate])
}

/** Text fields and anything that already scrolls sideways keep the swipe for themselves. */
function hasOwnGesture(target: Element): boolean {
  if (target.closest('input, textarea, select, [contenteditable="true"], dialog')) return true
  for (let el: Element | null = target; el; el = el.parentElement) {
    const overflow = getComputedStyle(el).overflowX
    if ((overflow === 'auto' || overflow === 'scroll') && el.scrollWidth > el.clientWidth) return true
  }
  return false
}
