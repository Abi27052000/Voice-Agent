import { useCallback, useEffect, useRef, useState } from 'react'
import VapiModule from '@vapi-ai/web'

// @vapi-ai/web ships CommonJS (`exports.default = Vapi`). Depending on the bundler's
// interop, the default import is either the class or `{ default: Vapi }`.
const Vapi = VapiModule.default ?? VapiModule

function describeError(err) {
  if (!err) return 'Something went wrong with the call.'
  if (typeof err === 'string') return err
  return (
    err.error?.message?.msg ||
    err.error?.message ||
    err.errorMsg ||
    err.message ||
    'Something went wrong with the call.'
  )
}

/**
 * Wraps the Vapi Web SDK for one browser call at a time.
 * status: 'idle' | 'connecting' | 'active' | 'ending'
 * transcript: one entry per speaker turn:
 *   { role: 'assistant' | 'user', speaker, text, partial } or { role: 'event', text }
 * personas maps Vapi assistant names to persona names (e.g. "Ridgeway Receptionist" -> "Alex").
 */
export function useVapiCall(publicKey, personas = {}) {
  const vapiRef = useRef(null)
  const personasRef = useRef(personas)
  const agentRef = useRef(null)
  const [agent, setAgent] = useState(null)
  const [status, setStatus] = useState('idle')
  const [transcript, setTranscript] = useState([])
  const [assistantSpeaking, setAssistantSpeaking] = useState(false)
  const [volume, setVolume] = useState(0)
  const [muted, setMuted] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    personasRef.current = personas
  }, [personas])

  useEffect(() => {
    if (!publicKey) return undefined
    const vapi = new Vapi(publicKey)
    vapiRef.current = vapi

    vapi.on('call-start', () => setStatus('active'))
    vapi.on('call-end', () => {
      setStatus('idle')
      setAssistantSpeaking(false)
      setVolume(0)
      setMuted(false)
    })
    vapi.on('speech-start', () => setAssistantSpeaking(true))
    vapi.on('speech-end', () => setAssistantSpeaking(false))
    vapi.on('volume-level', setVolume)
    vapi.on('error', (err) => {
      const text = describeError(err)
      setStatus('idle')
      // The audio layer reports a normal hang-up by the assistant as "Meeting has ended".
      if (/meeting (has )?ended/i.test(text)) return
      setError(text)
    })
    vapi.on('message', (msg) => {
      // A squad handoff (or the first assistant joining) announces the new speaker.
      if (msg?.type === 'assistant.started') {
        const vapiName = msg.newAssistant?.name
        const name = personasRef.current[vapiName] || vapiName || 'Assistant'
        const isHandoff = agentRef.current && agentRef.current !== name
        agentRef.current = name
        setAgent(name)
        if (isHandoff) {
          setTranscript((prev) => [...prev, { role: 'event', text: `${name} joined the call` }])
        }
        return
      }

      if (msg?.type !== 'transcript' || !msg.transcript) return
      const final = msg.transcriptType === 'final'
      const chunk = msg.transcript.trim()
      const speaker = msg.role === 'assistant' ? agentRef.current : null
      setTranscript((prev) => {
        const last = prev[prev.length - 1]
        // Vapi sends one sentence at a time, as partials then a final. Merge a
        // speaker's consecutive sentences into one bubble; `partial` holds the
        // sentence still being recognized.
        if (last && last.role === msg.role && last.speaker === speaker) {
          const updated = final
            ? { ...last, text: [last.text, chunk].filter(Boolean).join(' '), partial: '' }
            : { ...last, partial: chunk }
          return [...prev.slice(0, -1), updated]
        }
        return [...prev, { role: msg.role, speaker, text: final ? chunk : '', partial: final ? '' : chunk }]
      })
    })

    return () => {
      vapi.removeAllListeners()
      vapi.stop().catch(() => {})
      vapiRef.current = null
    }
  }, [publicKey])

  /** target: { assistantId } or { squadId }, plus optional assistant overrides. */
  const start = useCallback(async ({ assistantId, squadId, overrides, initialAgent } = {}) => {
    const vapi = vapiRef.current
    if (!vapi || !(assistantId || squadId)) return
    setError(null)
    setTranscript([])
    agentRef.current = initialAgent ?? null
    setAgent(initialAgent ?? null)
    setStatus('connecting')
    try {
      const call = squadId
        ? await vapi.start(undefined, overrides, squadId)
        : await vapi.start(assistantId, overrides)
      if (!call) setStatus('idle') // start failed; the 'error' event carries the reason
    } catch (err) {
      setError(describeError(err))
      setStatus('idle')
    }
  }, [])

  const stop = useCallback(() => {
    const vapi = vapiRef.current
    if (!vapi) return
    setStatus('ending')
    vapi.stop().catch((err) => setError(describeError(err)))
  }, [])

  const toggleMute = useCallback(() => {
    const vapi = vapiRef.current
    if (!vapi) return
    const next = !vapi.isMuted()
    vapi.setMuted(next)
    setMuted(next)
  }, [])

  return {
    status,
    agent,
    transcript,
    assistantSpeaking,
    volume,
    muted,
    error,
    ready: Boolean(publicKey),
    start,
    stop,
    toggleMute,
  }
}
