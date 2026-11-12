import { useEffect, useState } from 'react'
import { CallView } from '../components/CallWidget'
import { useVapiCall } from '../hooks/useVapiCall'
import { apiGet, apiPost } from '../lib/api'

const EMPTY = { full_name: '', phone: '', address: '', service: '', details: '', consent: false }

export default function QuoteRequest({ config }) {
  const call = useVapiCall(config?.public_key, config?.personas)
  const [services, setServices] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [submittedAt, setSubmittedAt] = useState(null)
  const [leadId, setLeadId] = useState(null)

  useEffect(() => {
    apiGet('/quote-requests/services')
      .then(setServices)
      .catch((err) => setError(err.message))
  }, [])

  const inCall = call.status !== 'idle'
  const update = (field) => (e) =>
    setForm((f) => ({ ...f, [field]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    setSubmittedAt(Date.now())
    try {
      const { address, ...rest } = form
      const res = await apiPost('/quote-requests', { ...rest, ...(address.trim() ? { address } : {}) })
      setLeadId(res.lead_id)
      // Speed-to-lead: call the lead back the moment the request is saved.
      await call.start({
        assistantId: res.assistant_id,
        overrides: { variableValues: res.variable_values },
        initialAgent: 'Sam',
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const speedSeconds = call.startedAt && submittedAt ? (call.startedAt - submittedAt) / 1000 : null

  return (
    <div className="layout">
      <section className="card">
        <h2>Request a quote</h2>
        <p className="muted small">Tell us what's going on. We'll call you right back, usually within seconds.</p>

        <form className="form" onSubmit={onSubmit}>
          <label>
            Full name
            <input required minLength={2} value={form.full_name} onChange={update('full_name')} autoComplete="name" disabled={inCall} />
          </label>
          <label>
            Phone
            <input required type="tel" value={form.phone} onChange={update('phone')} autoComplete="tel" disabled={inCall} />
          </label>
          <label>
            Service address <span className="muted small">(optional)</span>
            <input value={form.address} onChange={update('address')} autoComplete="street-address" disabled={inCall} />
          </label>
          <label>
            What do you need?
            <select required value={form.service} onChange={update('service')} disabled={inCall}>
              <option value="" disabled>
                Choose a service
              </option>
              {services.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Details <span className="muted small">(optional)</span>
            <textarea rows={3} maxLength={500} value={form.details} onChange={update('details')} disabled={inCall} />
          </label>
          <label className="checkbox">
            <input type="checkbox" required checked={form.consent} onChange={update('consent')} disabled={inCall} />
            <span className="small">
              I agree that Ridgeway Plumbing &amp; Air may call me at this number about my request using
              automated technology, including an AI voice assistant. Consent is not a condition of purchase.
            </span>
          </label>

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}

          <button className="btn btn-primary" type="submit" disabled={submitting || inCall || !call.ready}>
            {submitting ? 'Sending…' : 'Get my quote'}
          </button>
        </form>
      </section>

      <div className="stack">
        {speedSeconds != null && (
          <div className="speed-banner" role="status">
            <span className="speed-value">{speedSeconds.toFixed(1)}s</span>
            <span>
              from form submit to Sam calling back
              <span className="muted small block">
                Demo: the call rings in your browser. In production it dials the lead's phone.
              </span>
            </span>
          </div>
        )}
        <CallView
          call={call}
          agentName="Sam"
          title="Instant callback"
          subtitle="Sam calls the moment the form is submitted"
        />
        {leadId && !inCall && call.startedAt && (
          <p className="muted small">
            Saved as lead #{leadId}. See the outcome on the <a href="#/dashboard">dashboard</a>.
          </p>
        )}
      </div>
    </div>
  )
}
