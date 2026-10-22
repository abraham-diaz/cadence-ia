import { useState } from 'react'
import { requestAssessment } from '../../api/sessions.ts'
import type { Assessment } from '../../api/types.ts'
import { formatShortDate } from '../../shared/format.ts'
import './assessment.css'

interface Props {
  sessionId: string
  assessment: Assessment | null
  onChange: (assessment: Assessment) => void
}

/** The AI coach's written assessment, or a button to ask for one. */
export default function AssessmentCard({ sessionId, assessment, onChange }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function ask() {
    setLoading(true)
    setError(null)
    try {
      onChange(await requestAssessment(sessionId))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  if (!assessment) {
    return (
      <section className="card assessment">
        <h2>Valoración</h2>
        <p className="muted small">
          Un entrenador IA (Gemini) comenta la sesión a partir de tus métricas. Solo se envían las cifras:
          ni el archivo, ni el GPS, ni datos tuyos.
        </p>
        <button type="button" className="button" onClick={ask} disabled={loading}>
          {loading ? 'Pensando…' : 'Pedir valoración'}
        </button>
        {error && <p className="form-error">{error}</p>}
      </section>
    )
  }

  return (
    <section className="card assessment" aria-busy={loading}>
      <p className="eyebrow">Valoración</p>
      <h2 className="assessment-headline">{assessment.headline}</h2>
      <p>{assessment.summary}</p>

      <AssessmentList title="Lo mejor" items={assessment.strengths} kind="good" />
      <AssessmentList title="A mejorar" items={assessment.improvements} kind="improve" />

      <div className="assessment-advice">
        <p className="assessment-subtitle">Para la próxima</p>
        <p>{assessment.advice}</p>
      </div>

      <div className="assessment-footer">
        <span className="muted small">
          {assessment.model} · {formatShortDate(assessment.created_at)}
        </span>
        <button type="button" className="link-button" onClick={ask} disabled={loading}>
          {loading ? 'Pensando…' : 'Regenerar'}
        </button>
      </div>
      {error && <p className="form-error">{error}</p>}
    </section>
  )
}

function AssessmentList({ title, items, kind }: { title: string; items: string[]; kind: 'good' | 'improve' }) {
  if (!items.length) return null
  return (
    <div>
      <p className="assessment-subtitle">{title}</p>
      <ul className={`assessment-list assessment-list-${kind}`}>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  )
}
