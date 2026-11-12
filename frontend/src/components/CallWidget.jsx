import { useEffect, useRef } from 'react'
import { useVapiCall } from '../hooks/useVapiCall'

const STATUS_LABEL = {
  idle: 'Ready',
  connecting: 'Connecting…',
  active: 'On call',
  ending: 'Ending…',
}

/**
 * Starts a browser call with a squad (preferred) or a single assistant.
 * `agentName` is who answers first; `personas` maps Vapi assistant names to
 * persona names so squad handoffs are labelled in the transcript.
 */
export default function CallWidget({
  publicKey,
  assistantId,
  squadId,
  personas,
  agentName,
  subtitle,
  maxMinutes = 10,
}) {
  const call = useVapiCall(publicKey, personas)
  const transcriptRef = useRef(null)
  const inCall = call.status !== 'idle'
  const speakingAgent = call.agent || agentName

  useEffect(() => {
    const el = transcriptRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [call.transcript])

  const startCall = () =>
    call.start(squadId ? { squadId, initialAgent: agentName } : { assistantId, initialAgent: agentName })

  return (
    <section className="card call-widget" aria-label={`Call ${agentName}`}>
      <div className="call-header">
        <div>
          <h2>Talk to {agentName}</h2>
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
          <button className="btn btn-primary" onClick={startCall} disabled={!call.ready || !(squadId || assistantId)}>
            Start call
          </button>
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
