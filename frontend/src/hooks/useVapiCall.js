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
 * transcript: [{ role: 'assistant' | 'user', text, partial }]  (one entry per speaker turn)
 */
export function useVapiCall(publicKey) {
  const vapiRef = useRef(null)
  const [status, setStatus] = useState('idle')
  const [transcript, setTranscript] = useState([])
  const [assistantSpeaking, setAssistantSpeaking] = useState(false)
  const [volume, setVolume] = useState(0)
  const [muted, setMuted] = useState(false)
  const [error, setError] = useState(null)

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
      setError(describeError(err))
      setStatus('idle')
    })
    vapi.on('message', (msg) => {
      if (msg?.type !== 'transcript' || !msg.transcript) return
      const final = msg.transcriptType === 'final'
      const chunk = msg.transcript.trim()
      setTranscript((prev) => {
        const last = prev[prev.length - 1]
        // Vapi sends one sentence at a time, as partials then a final. Merge a
        // speaker's consecutive sentences into one bubble; `partial` holds the
        // sentence still being recognized.
        if (last && last.role === msg.role) {
          const updated = final
            ? { ...last, text: [last.text, chunk].filter(Boolean).join(' '), partial: '' }
            : { ...last, partial: chunk }
          return [...prev.slice(0, -1), updated]
        }
        return [...prev, { role: msg.role, text: final ? chunk : '', partial: final ? '' : chunk }]
      })
    })

    return () => {
      vapi.removeAllListeners()
      vapi.stop().catch(() => {})
      vapiRef.current = null
    }
  }, [publicKey])

  const start = useCallback(async (assistantId, overrides) => {
    const vapi = vapiRef.current
    if (!vapi || !assistantId) return
    setError(null)
    setTranscript([])
    setStatus('connecting')
    try {
      const call = await vapi.start(assistantId, overrides)
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
