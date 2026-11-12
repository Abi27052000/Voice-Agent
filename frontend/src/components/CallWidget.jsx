import { useEffect, useRef } from 'react'
import { useVapiCall } from '../hooks/useVapiCall'

const STATUS_LABEL = {
  idle: 'Ready',
  connecting: 'Connecting…',
  active: 'On call',
  ending: 'Ending…',
}

/**
 * Presentational call panel for a `useVapiCall()` result. Pages that start calls
 * programmatically (e.g. after a form submit) own the hook and render this.
 */
export function CallView({ call, agentName, title, subtitle, maxMinutes = 10, onStart, canStart = true, startLabel = 'Start call' }) {
  const transcriptRef = useRef(null)
  const inCall = call.status !== 'idle'
  const speakingAgent = call.agent || agentName

  useEffect(() => {
    const el = transcriptRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [call.transcript])

  return (
    <section className="card call-widget" aria-label={title ?? `Call ${agentName}`}>
      <div className="call-header">
        <div>
          <h2>{title ?? `Talk to ${agentName}`}</h2>
          <p className="muted">
            {subtitle ?? 'Browser call · uses your microphone'} · ends after {maxMinutes} min
          </p>
        </div>
        <span className={`status status-${call.status}`}>
          <span className="dot" aria-hidden="true" />
          {call.status === 'active' ? `On call with ${speakingAgent}` : STATUS_LABEL[call.status]}
        </span>
      </div>

      <div className="call-controls">
        {inCall ? (
          <button className="btn btn-danger" onClick={call.stop} disabled={call.status === 'ending'}>
            End call
          </button>
        ) : (
          onStart && (
            <button className="btn btn-primary" onClick={onStart} disabled={!call.ready || !canStart}>
              {startLabel}
            </button>
          )
        )}
        <button
          className="btn btn-ghost"
          onClick={call.toggleMute}
          disabled={call.status !== 'active'}
          aria-pressed={call.muted}
        >
          {call.muted ? 'Unmute' : 'Mute'}
        </button>
        <div className="meter" aria-label={call.assistantSpeaking ? `${speakingAgent} is speaking` : 'Listening'}>
          <div className="meter-fill" style={{ transform: `scaleX(${Math.min(1, call.volume * 1.5)})` }} />
        </div>
        <span className="muted small">
          {call.status === 'active' ? (call.assistantSpeaking ? `${speakingAgent} speaking` : 'Listening') : ''}
        </span>
      </div>

      {call.error && (
        <p className="error" role="alert">
          {call.error}
        </p>
      )}

      <div className="transcript" ref={transcriptRef} aria-live="polite">
        {call.transcript.length === 0 ? (
          <p className="muted placeholder">The live transcript appears here once the call starts.</p>
        ) : (
          call.transcript.map((line, i) =>
            line.role === 'event' ? (
              <p key={i} className="line-event">
                <span>{line.text}</span>
              </p>
            ) : (
              <p key={i} className={`line line-${line.role}`}>
                <span className="who">{line.role === 'assistant' ? line.speaker || agentName : 'You'}</span>
                {line.text}
                {line.partial && <span className="partial">{line.text ? ' ' : ''}{line.partial}</span>}
              </p>
            ),
          )
        )}
      </div>
    </section>
  )
}

/**
 * Self-contained call panel: starts a call with a squad (preferred) or a single
 * assistant when the user clicks Start. `personas` maps Vapi assistant names to
 * persona names so squad handoffs are labelled in the transcript.
 */
export default function CallWidget({ publicKey, assistantId, squadId, personas, agentName, ...viewProps }) {
  const call = useVapiCall(publicKey, personas)
  const startCall = () =>
    call.start(squadId ? { squadId, initialAgent: agentName } : { assistantId, initialAgent: agentName })
  return (
    <CallView call={call} agentName={agentName} onStart={startCall} canStart={Boolean(squadId || assistantId)} {...viewProps} />
  )
}
