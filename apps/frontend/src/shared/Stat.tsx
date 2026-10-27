import { formatSigned } from './format.ts'
import './Stat.css'

interface Props {
  label: string
  value: string | number
  unit?: string
  /** Difference with the average of previous sessions, already in display units. */
  delta?: number | null
  deltaUnit?: string
}

export default function Stat({ label, value, unit, delta, deltaUnit = '' }: Props) {
  const hasDelta = delta !== undefined && delta !== null
  const rounded = hasDelta ? Math.round(delta) : 0

  return (
    <div className="card stat">
      <p className="stat-label">{label}</p>
      <p className="stat-value">
        {value}
        {unit && <small> {unit}</small>}
      </p>
      {hasDelta && (
        <p className="stat-delta">
          {rounded === 0 ? (
            'igual que tu media'
          ) : (
            <>
              <span aria-hidden="true">{rounded > 0 ? '▲' : '▼'}</span> {formatSigned(delta)}
              {deltaUnit} vs media
            </>
          )}
        </p>
      )}
    </div>
  )
}
