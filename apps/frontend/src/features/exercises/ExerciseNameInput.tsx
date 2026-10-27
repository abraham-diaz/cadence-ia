import { useEffect, useState } from 'react'
import { searchExercises } from '../../api/exercises.ts'
import type { CatalogExercise } from '../../api/types.ts'
import './exercises.css'

interface Props {
  name: string
  catalogId: number | null
  onChange: (name: string, catalogId: number | null) => void
}

/** Free text, with catalog matches to pick from: a picked one gets its "how to" page. */
export default function ExerciseNameInput({ name, catalogId, onChange }: Props) {
  const [focused, setFocused] = useState(false)
  const [matches, setMatches] = useState<CatalogExercise[]>([])
  const query = name.trim()
  const searching = focused && catalogId === null && query.length >= 2

  useEffect(() => {
    if (!searching) return
    let cancelled = false
    // Wait until typing pauses, not one request per letter.
    const timer = window.setTimeout(() => {
      searchExercises(query)
        .then((found) => !cancelled && setMatches(found))
        .catch(() => !cancelled && setMatches([]))
    }, 250)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [searching, query])

  const open = searching && matches.length > 0

  return (
    <div className="exercise-name">
      <input
        className="text-input"
        placeholder="Ejercicio, p. ej. press de banca"
        aria-label="Ejercicio"
        aria-autocomplete="list"
        maxLength={80}
        value={name}
        // Typing over a picked exercise unlinks it: the name may no longer be that one.
        onChange={(e) => onChange(e.target.value, null)}
        onFocus={() => setFocused(true)}
        // Later than a tap on a match, so the tap still lands.
        onBlur={() => window.setTimeout(() => setFocused(false), 150)}
      />
      {catalogId !== null && <p className="exercise-linked small">✓ Con ficha de cómo se hace</p>}
      {open && (
        <ul className="exercise-matches" role="listbox">
          {matches.map((match) => (
            <li key={match.id} role="option" aria-selected={false}>
              <button
                type="button"
                className="exercise-match"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onChange(match.name, match.id)
                  setMatches([])
                }}
              >
                {match.image_url ? (
                  <img src={match.image_url} alt="" loading="lazy" className="exercise-thumb exercise-thumb-small" />
                ) : (
                  <span className="exercise-thumb exercise-thumb-small" aria-hidden="true" />
                )}
                <span>{match.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
