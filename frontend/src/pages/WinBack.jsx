import { useCallback, useEffect, useRef, useState } from 'react'
import { LeadStatusBadge } from '../components/Badge'
import { CallView } from '../components/CallWidget'
import StatTile from '../components/StatTile'
import { usePolling } from '../hooks/usePolling'
import { useVapiCall } from '../hooks/useVapiCall'
import { apiGet, apiPost } from '../lib/api'
import { phone } from '../lib/format'

const loadOverview = () => apiGet('/win-back')

export default function WinBack({ config }) {
  const call = useVapiCall(config?.public_key, config?.personas)
  const { data, error, refresh } = usePolling(loadOverview, 10000)
  const [activeLead, setActiveLead] = useState(null)
  const [startError, setStartError] = useState(null)
  const inCall = call.status !== 'idle'

  // Refresh right after a call ends so the new status shows without waiting for the next poll.
  const wasInCall = useRef(false)
  useEffect(() => {
    if (wasInCall.current && !inCall) {
      const timer = setTimeout(refresh, 1500)
      wasInCall.current = false
      return () => clearTimeout(timer)
    }
    wasInCall.current = inCall
    return undefined
  }, [inCall, refresh])

  const startCall = useCallback(
    async (lead) => {
      setStartError(null)
      setActiveLead(lead)
      try {
        const res = await apiPost(`/win-back/leads/${lead.id}/call`, {})
        await call.start({
          assistantId: res.assistant_id,
          overrides: { variableValues: res.variable_values },
          initialAgent: 'Taylor',
        })
      } catch (err) {
        setStartError(err.message)
      }
    },
    [call],
  )

  if (!data) {
    return error ? <p className="error">{error}</p> : <p className="muted">Loading win-back campaign…</p>
  }

  const { summary, leads, offer } = data

  return (
    <div className="dashboard">
      <section className="card">
        <h2>Win-back campaign</h2>
        <p className="muted small">
          Past customers who went quiet get a call from Taylor with this season's offer:{' '}
          <strong>
            {offer.offer} for {offer.offer_price}
          </strong>{' '}
          until {offer.offer_deadline}. Opt-outs are recorded and never called again.
        </p>
      </section>

      <div className="kpi-row">
        <StatTile label="Past customers" value={summary.total} detail={`${summary.callable} still callable`} />
        <StatTile label="Reached" value={summary.contacted} detail="called at least once" />
        <StatTile label="Reactivated" value={summary.booked} detail="booked a visit" />
        <StatTile label="Callbacks" value={summary.callbacks} detail="asked for a later call" />
        <StatTile
          label="Opted out"
          value={summary.opted_out}
          detail={`${summary.not_interested} more not interested`}
        />
      </div>

      <div className="layout">
        <section className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Last service</th>
                  <th className="num">Months ago</th>
                  <th>Status</th>
                  <th aria-label="Action" />
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id} className={activeLead?.id === lead.id && inCall ? 'row-active' : ''}>
                    <td>
                      {lead.name}
                      <span className="muted small block">{phone(lead.phone)}</span>
                    </td>
                    <td>{lead.last_service}</td>
                    <td className="num">{lead.months_since}</td>
                    <td>
                      <LeadStatusBadge status={lead.status} />
                    </td>
                    <td className="num">
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => startCall(lead)}
                        disabled={!lead.callable || inCall || !call.ready}
                        title={lead.callable ? `Call ${lead.name}` : 'Not callable'}
                      >
                        Call
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted small">
            Demo: calls ring in your browser and you play the customer. In production the same assistant runs as a
            Vapi Campaign; <code>scripts/export_campaign.py</code> writes the contact CSV and request.
          </p>
        </section>

        <div className="stack sticky">
          {startError && (
            <p className="error" role="alert">
              {startError}
            </p>
          )}
          <CallView
            call={call}
            agentName="Taylor"
            title={activeLead ? `Calling ${activeLead.name}` : 'Win-back call'}
            subtitle={activeLead ? `Last service: ${activeLead.last_service}` : 'Pick a customer to call'}
          />
        </div>
      </div>
    </div>
  )
}
