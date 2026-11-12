import { useEffect, useState } from 'react'
import { apiGet } from '../lib/api'
import { cents, dateTime, duration, humanize, money } from '../lib/format'
import { CallOutcomeBadges } from './Badge'

// Vapi's saved transcript doesn't say which squad member spoke, so stay neutral.
const SPEAKERS = { AI: 'Ridgeway AI', User: 'Caller', Bot: 'Ridgeway AI', Assistant: 'Ridgeway AI' }

// Vapi transcripts look like "AI: ...\nUser: ...".
function parseTranscript(text) {
  return (text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const match = line.match(/^(\w+):\s*(.*)$/)
      return match && SPEAKERS[match[1]]
        ? { who: SPEAKERS[match[1]], role: match[1] === 'User' ? 'user' : 'assistant', text: match[2] }
        : { who: '', role: 'assistant', text: line }
    })
}

export default function CallDetailPanel({ callId, now, onClose }) {
  const [result, setResult] = useState({ id: null, call: null, error: null })

  useEffect(() => {
    let cancelled = false
    apiGet(`/calls/${callId}`)
      .then((call) => !cancelled && setResult({ id: callId, call, error: null }))
      .catch((err) => !cancelled && setResult({ id: callId, call: null, error: err.message }))
    return () => {
      cancelled = true
    }
  }, [callId])

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const { call, error } = result.id === callId ? result : { call: null, error: null }

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Call details" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h2>Call details</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            Close
          </button>
        </div>

        {error && <p className="error">{error}</p>}
        {!call && !error && <p className="muted">Loading…</p>}

        {call && (
          <>
            <CallOutcomeBadges call={call} now={now} />
            <dl className="facts">
              <dt>Started</dt>
              <dd>{dateTime(call.started_at)}</dd>
              <dt>Duration</dt>
              <dd>{duration(call.duration_seconds)}</dd>
              <dt>Cost</dt>
              <dd>{cents(call.cost_usd)}</dd>
              <dt>Ended</dt>
              <dd>{humanize(call.ended_reason)}</dd>
              <dt>Caller</dt>
              <dd>{call.lead_name ?? '—'}</dd>
              <dt>Job type</dt>
              <dd>{humanize(call.job_type)}</dd>
              <dt>Urgency</dt>
              <dd>{humanize(call.urgency)}</dd>
              <dt>Sentiment</dt>
              <dd>{humanize(call.caller_sentiment)}</dd>
              <dt>Est. value</dt>
              <dd>{money(call.estimated_value_usd)}</dd>
            </dl>

            {call.follow_up_needed && call.follow_up_reason && (
              <div className="callout callout-warning">
                <strong>Follow-up:</strong> {call.follow_up_reason}
              </div>
            )}

            <section>
              <h3>Summary</h3>
              <p>{call.summary || <span className="muted">No summary for this call.</span>}</p>
            </section>

            <section>
              <h3>Transcript</h3>
              <div className="transcript transcript-static">
                {call.transcript ? (
                  parseTranscript(call.transcript).map((line, i) => (
                    <p key={i} className={`line line-${line.role}`}>
                      {line.who && <span className="who">{line.who}</span>}
                      {line.text}
                    </p>
                  ))
                ) : (
                  <p className="muted">No transcript.</p>
                )}
              </div>
            </section>
          </>
        )}
      </aside>
    </div>
  )
}
