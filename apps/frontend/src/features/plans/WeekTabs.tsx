import { weekLetter } from './weeks.ts'

interface Props {
  weeks: number
  selected: number
  onSelect: (week: number) => void
}

/** "Semana A", "Semana B"... Nothing when the plan has a single week. */
export default function WeekTabs({ weeks, selected, onSelect }: Props) {
  if (weeks < 2) return null
  return (
    <div
      className="segmented"
      role="tablist"
      aria-label="Semana"
      style={{ gridTemplateColumns: `repeat(${weeks}, 1fr)` }}
    >
      {Array.from({ length: weeks }, (_, week) => (
        <button
          key={week}
          type="button"
          role="tab"
          aria-selected={selected === week}
          className={selected === week ? 'selected' : ''}
          onClick={() => onSelect(week)}
        >
          Semana {weekLetter(week)}
        </button>
      ))}
    </div>
  )
}
