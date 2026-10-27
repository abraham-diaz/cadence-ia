import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useLayoutEffect, useRef, useState } from 'react'
import { fetchWeekProgress } from '../../api/plans.ts'
import type { SessionSummary, WeekProgress } from '../../api/types.ts'
import { localIsoDate, parseIsoDate, weekLabel } from '../../shared/format.ts'
import { useFetch } from '../../shared/useFetch.ts'
import WeekStrip from './WeekStrip.tsx'

interface Props {
  current: WeekProgress
  firstWeek: string // Monday of the oldest week that can be shown
  today: string
  sessions: Map<string, SessionSummary>
}

/** This week and, swiping right, the ones before it. */
export default function WeekCarousel({ current, firstWeek, today, sessions }: Props) {
  const weeks = mondaysBetween(firstWeek, current.start)
  const scroller = useRef<HTMLDivElement>(null)
  const card = useRef<HTMLElement>(null)
  // Counted from the end, so older weeks loading in don't move the one on screen.
  const [weeksAgo, setWeeksAgo] = useState(0)
  const index = weeks.length - 1 - weeksAgo

  useLayoutEffect(() => {
    const el = scroller.current
    if (!el) return
    el.scrollLeft = index * el.clientWidth
    moveIndicator()
    // Only when the list of weeks changes: while swiping, the scroll position leads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weeks.length])

  // Set straight on the DOM: re-rendering on every scroll frame would stutter.
  function moveIndicator() {
    const el = scroller.current
    const max = el ? el.scrollWidth - el.clientWidth : 0
    card.current?.style.setProperty('--week-pos', String(el && max > 0 ? el.scrollLeft / max : 1))
  }

  function onScroll() {
    const el = scroller.current
    if (!el) return
    moveIndicator()
    const visible = Math.round(el.scrollLeft / el.clientWidth)
    setWeeksAgo(weeks.length - 1 - visible)
  }

  function go(to: number) {
    const el = scroller.current
    el?.scrollTo({ left: to * el.clientWidth, behavior: 'smooth' })
  }

  return (
    <section className="card week-card" ref={card}>
      <div className="week-nav">
        <h2>{weekLabel(parseIsoDate(weeks[index]))}</h2>
        <div className="week-arrows">
          <button
            type="button"
            className="week-arrow"
            onClick={() => go(index - 1)}
            disabled={index === 0}
            aria-label="Semana anterior"
          >
            <ChevronLeft size={20} />
          </button>
          <button
            type="button"
            className="week-arrow"
            onClick={() => go(index + 1)}
            disabled={weeksAgo === 0}
            aria-label="Semana siguiente"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

      <div className="week-viewport">
        <div className="week-carousel" ref={scroller} onScroll={onScroll}>
          {weeks.map((start, i) => (
            <div key={start} className="week-slide" aria-hidden={i !== index}>
              {i === weeks.length - 1 ? (
                <WeekStrip progress={current} today={today} sessions={sessions} />
              ) : (
                Math.abs(i - index) <= 1 && <PastWeek start={start} today={today} sessions={sessions} />
              )}
            </div>
          ))}
        </div>
      </div>

      {weeks.length > 1 && (
        <div className="week-indicator" aria-hidden="true">
          <span style={{ width: `${Math.max(100 / weeks.length, 20)}%` }} />
        </div>
      )}
    </section>
  )
}

/** Fetched only when it's on screen or next to it. */
function PastWeek({ start, ...props }: { start: string; today: string; sessions: Map<string, SessionSummary> }) {
  const { state } = useFetch(() => fetchWeekProgress(start), `week-progress:${start}`)
  if (state.status === 'ok') return <WeekStrip progress={state.data} {...props} />
  if (state.status === 'error') return <p className="muted small">No se pudo cargar esta semana.</p>
  return null
}

/** Oldest first, at most two years back. */
function mondaysBetween(first: string, last: string): string[] {
  const mondays = [last]
  const day = parseIsoDate(last)
  while (mondays.length < 104) {
    day.setDate(day.getDate() - 7)
    if (localIsoDate(day) < first) break
    mondays.unshift(localIsoDate(day))
  }
  return mondays
}
