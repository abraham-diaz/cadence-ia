import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { fetchWeekSummary, proposePlan, sendPlanChat } from '../../api/plans.ts'
import type { ChatMessage } from '../../api/types.ts'
import { loadChat, saveChat } from './chatStorage.ts'
import { fromProposal, saveDraft } from './planDraft.ts'
import './plans.css'

const SUGGESTIONS = [
  'Quiero ganar fondo para el frontón sin dejar las pesas',
  'Hazme un plan de 4 días a la semana',
  'Me cuesta ser constante, ¿por dónde empiezo?',
]

// How the backend's summary starts (domain/week_summary.py).
const WEEK_SUMMARY_TITLE = 'Mis últimos entrenos de la semana ('

export default function PlanChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(loadChat)
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const [sharing, setSharing] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [planError, setPlanError] = useState<string | null>(null)
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  // Read from the text itself, so it survives a reload and comes back after "Empezar de nuevo".
  const weekShared = [draft, ...messages.map((m) => m.text)].some((text) => text.includes(WEEK_SUMMARY_TITLE))
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => saveChat(messages), [messages])

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [messages, pending, error])

  async function ask(conversation: ChatMessage[]) {
    setMessages(conversation)
    setPending(true)
    setError(null)
    try {
      const { reply } = await sendPlanChat(conversation)
      setMessages([...conversation, { role: 'model', text: reply }])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setPending(false)
    }
  }

  function send(text: string) {
    const clean = text.trim()
    if (!clean || pending) return
    setDraft('')
    resize(inputRef.current, '')
    ask([...messages, { role: 'user', text: clean }])
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    send(draft)
  }

  // On a phone Enter adds a line; on the PC Ctrl/Cmd+Enter sends.
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) send(draft)
  }

  // Written into the box, not sent: the user sees exactly what Gemini will get.
  async function shareWeek() {
    setSharing(true)
    setError(null)
    try {
      const { text } = await fetchWeekSummary()
      const next = draft.trim() ? `${draft.trimEnd()}\n\n${text}` : text
      setDraft(next)
      requestAnimationFrame(() => {
        resize(inputRef.current, next)
        inputRef.current?.focus()
      })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSharing(false)
    }
  }

  async function adoptPlan() {
    setExtracting(true)
    setPlanError(null)
    try {
      saveDraft(fromProposal(await proposePlan(messages)))
      navigate('/plan/revisar')
    } catch (err) {
      setPlanError((err as Error).message)
      setExtracting(false)
    }
  }

  const coachReplied = messages.some((m) => m.role === 'model')

  function restart() {
    if (!window.confirm('¿Borrar la conversación y empezar de nuevo?')) return
    setMessages([])
    setError(null)
  }

  return (
    <main className="page chat-page">
      <nav className="top-bar chat-top-bar">
        <Link to="/" className="back-link">
          ‹ Entrenamientos
        </Link>
        {messages.length > 0 && (
          <button type="button" className="link-button" onClick={restart} disabled={pending}>
            Empezar de nuevo
          </button>
        )}
      </nav>

      <header className="page-header">
        <p className="eyebrow">Plan</p>
        <h1>Nuevo plan</h1>
      </header>

      {messages.length === 0 && (
        <section className="chat-intro">
          <p className="muted">
            Cuéntale al entrenador IA (Gemini) qué quieres conseguir y diseñad juntos tu semana. Solo conoce los
            nombres de tus tipos de entrenamiento: si quieres que sepa lo que has hecho, comparte tu última semana.
          </p>
          <div className="chat-suggestions">
            {SUGGESTIONS.map((text) => (
              <button key={text} type="button" className="chip chip-button" onClick={() => send(text)}>
                {text}
              </button>
            ))}
          </div>
          <p className="muted small">Lo que escribas se envía a Google: no pongas datos personales.</p>
        </section>
      )}

      <ol className="chat-messages" aria-live="polite">
        {messages.map((message, i) => (
          <li key={i} className={`chat-bubble chat-bubble-${message.role}`}>
            {message.text}
          </li>
        ))}
        {pending && <li className="chat-bubble chat-bubble-model chat-typing">Pensando…</li>}
      </ol>

      {error && (
        <div className="chat-error">
          <p className="form-error">{error}</p>
          <button type="button" className="link-button" onClick={() => ask(messages)}>
            Reintentar
          </button>
        </div>
      )}
      <div ref={endRef} />

      <form className="chat-composer" onSubmit={onSubmit}>
        {planError && <p className="form-error">{planError}</p>}
        <div className="chat-tools">
          {!weekShared && (
            <button type="button" className="link-button" onClick={shareWeek} disabled={sharing}>
              {sharing ? 'Preparando…' : '+ Compartir mi última semana'}
            </button>
          )}
          {coachReplied && (
            <button
              type="button"
              className="button button-small chat-use-plan"
              onClick={adoptPlan}
              disabled={pending || extracting}
            >
              {extracting ? 'Leyendo el plan…' : 'Usar este plan'}
            </button>
          )}
        </div>
        <div className="chat-input-row">
          <textarea
            ref={inputRef}
            className="text-input chat-input"
            rows={1}
            placeholder="Escribe un mensaje"
            aria-label="Mensaje"
            value={draft}
            maxLength={4000}
            onChange={(event) => {
              setDraft(event.target.value)
              resize(event.target, event.target.value)
            }}
            onKeyDown={onKeyDown}
          />
          <button
            type="submit"
            className="button chat-send"
            disabled={pending || !draft.trim()}
            aria-label="Enviar"
          >
            ↑
          </button>
        </div>
      </form>
    </main>
  )
}

// Grows with the text up to the max-height set in CSS.
function resize(textarea: HTMLTextAreaElement | null, value: string) {
  if (!textarea) return
  textarea.style.height = 'auto'
  if (value) textarea.style.height = `${textarea.scrollHeight}px`
}
