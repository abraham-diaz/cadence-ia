import type { Segment } from '../api.ts'
import { formatClock } from '../format.ts'

export default function SegmentList({ segments }: { segments: Segment[] }) {
  // Number only the sets: "Serie 1", "Descanso", "Serie 2", ...
  const setNumbers = segments.map(
    (_, i) => segments.slice(0, i + 1).filter((s) => s.kind === 'work').length,
  )

  return (
    <ol className="segment-list">
      {segments.map((s, i) => {
        return (
          <li key={s.start_s} className={`segment segment-${s.kind}`}>
            <div className="segment-main">
              <p className="segment-title">{s.kind === 'work' ? `Serie ${setNumbers[i]}` : 'Descanso'}</p>
              <p className="muted small">
                {formatClock(s.start_s)} · dura {formatClock(s.duration_s)}
              </p>
            </div>
            <div className="segment-hr">
              <p>
                {s.hr_start} → {s.hr_end} <small>ppm</small>
              </p>
              {s.kind === 'rest' && <Recovery segment={s} />}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function Recovery({ segment }: { segment: Segment }) {
  const parts = []
  if (segment.drop_30s !== null) parts.push(`−${segment.drop_30s} a 30 s`)
  if (segment.drop_60s !== null) parts.push(`−${segment.drop_60s} a 60 s`)
  return parts.length ? <p className="muted small">{parts.join(' · ')}</p> : null
}
