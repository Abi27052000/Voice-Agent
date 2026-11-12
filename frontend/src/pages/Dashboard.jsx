import { useCallback, useState } from 'react'
import Badge, { CallOutcomeBadges, LeadStatusBadge } from '../components/Badge'
import CallDetailPanel from '../components/CallDetailPanel'
import StatTile from '../components/StatTile'
import { usePolling } from '../hooks/usePolling'
import { apiGet } from '../lib/api'
import { cents, dateTime, duration, humanize, money, percent, phone } from '../lib/format'

const TABS = ['Calls', 'Appointments', 'Leads']

async function loadDashboard() {
  const [stats, calls, appointments, leads] = await Promise.all([
    apiGet('/stats'),
    apiGet('/calls'),
    apiGet('/appointments'),
    apiGet('/leads'),
  ])
  return { stats, calls, appointments, leads }
}

function KpiRow({ stats }) {
  return (
    <div className="kpi-row">
      <StatTile
        label="Calls handled"
        value={stats.calls_total}
        detail={`avg ${duration(stats.avg_duration_seconds)} per call`}
      />
      <StatTile
        label="Booking rate"
        value={percent(stats.booking_rate)}
        detail={`${stats.calls_booked} of ${stats.calls_with_outcome} analyzed calls`}
      />
      <StatTile label="Est. booked revenue" value={money(stats.est_booked_revenue_usd)} detail="typical job value" />
      <StatTile
        label="Needs follow-up"
        value={stats.follow_ups_open}
        detail={`${stats.emergencies} emergency lead${stats.emergencies === 1 ? '' : 's'}`}
      />
      <StatTile label="Upcoming visits" value={stats.upcoming_appointments} detail={`${stats.leads_total} leads in CRM`} />
      <StatTile
        label="Speed to lead"
        value={stats.speed_to_lead_seconds == null ? '—' : `${stats.speed_to_lead_seconds}s`}
        detail={`avg over ${stats.web_leads_called} web lead${stats.web_leads_called === 1 ? '' : 's'}`}
      />
      <StatTile
        label="AI cost per call"
        value={cents(stats.avg_cost_per_call_usd)}
        detail={`${cents(stats.total_cost_usd)} total`}
      />
    </div>
  )
}

function NeedsAttention({ calls, leads, onOpenCall }) {
  const emergencies = leads.filter((l) => l.status === 'emergency')
  // An emergency lead already covers the call that created it; don't list it twice.
  const emergencyLeadIds = new Set(emergencies.map((l) => l.id))
  const followUps = calls.filter((c) => c.follow_up_needed && !emergencyLeadIds.has(c.lead_id))
  if (!followUps.length && !emergencies.length) return null
  return (
    <section className="card">
      <h2>Needs attention</h2>
      <ul className="attention-list">
        {emergencies.map((lead) => (
          <li key={`lead-${lead.id}`}>
            <Badge tone="critical">Emergency</Badge>
            <span>
              <strong>{lead.name}</strong> · {phone(lead.phone)} · {lead.issue}
            </span>
          </li>
        ))}
        {followUps.map((call) => (
          <li key={`call-${call.id}`}>
            <Badge tone="warning">Follow-up</Badge>
            <button className="link-button" onClick={() => onOpenCall(call.id)}>
              {call.follow_up_reason || 'Review this call'}
            </button>
            <span className="muted small">{dateTime(call.started_at)}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function CallsTable({ calls, now, onOpenCall }) {
  if (!calls.length) return <p className="muted empty">No calls yet. Make one from the Front desk tab.</p>
  return (
    <table>
      <thead>
        <tr>
          <th>When</th>
          <th>Caller</th>
          <th>Job</th>
          <th>Outcome</th>
          <th className="num">Duration</th>
          <th className="num">Cost</th>
        </tr>
      </thead>
      <tbody>
        {calls.map((c) => (
          <tr key={c.id} className="clickable" onClick={() => onOpenCall(c.id)}>
            <td>
              <button className="link-button" onClick={() => onOpenCall(c.id)}>
                {dateTime(c.started_at)}
              </button>
            </td>
            <td>{c.lead_name ?? <span className="muted">Unknown</span>}</td>
            <td>{humanize(c.job_type)}</td>
            <td>
              <CallOutcomeBadges call={c} now={now} />
            </td>
            <td className="num">{duration(c.duration_seconds)}</td>
            <td className="num">{cents(c.cost_usd)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function AppointmentsTable({ appointments }) {
  if (!appointments.length) return <p className="muted empty">No appointments yet.</p>
  return (
    <table>
      <thead>
        <tr>
          <th>Ref</th>
          <th>Window</th>
          <th>Customer</th>
          <th>Address</th>
          <th>Issue</th>
        </tr>
      </thead>
      <tbody>
        {appointments.map((a) => (
          <tr key={a.id} className={a.is_past ? 'past' : ''}>
            <td>{a.reference}</td>
            <td>{a.window_label}</td>
            <td>
              {a.lead_name}
              <span className="muted small block">{phone(a.lead_phone)}</span>
            </td>
            <td>{a.lead_address ?? '—'}</td>
            <td>{a.issue ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function LeadsTable({ leads }) {
  if (!leads.length) return <p className="muted empty">No leads yet.</p>
  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Phone</th>
          <th>Status</th>
          <th>Issue</th>
          <th>Source</th>
          <th>Added</th>
        </tr>
      </thead>
      <tbody>
        {leads.map((l) => (
          <tr key={l.id}>
            <td>{l.name}</td>
            <td>{phone(l.phone)}</td>
            <td>
              <LeadStatusBadge status={l.status} />
            </td>
            <td>{l.issue ?? '—'}</td>
            <td>{humanize(l.source)}</td>
            <td>{dateTime(l.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function Dashboard() {
  const { data, error, updatedAt, refresh } = usePolling(loadDashboard, 10000)
  const [tab, setTab] = useState('Calls')
  const [openCallId, setOpenCallId] = useState(null)
  const closeCall = useCallback(() => setOpenCallId(null), [])

  if (!data) {
    return error ? (
      <section className="card">
        <h2>Couldn't load the dashboard</h2>
        <p className="error">{error}</p>
      </section>
    ) : (
      <p className="muted">Loading dashboard…</p>
    )
  }

  const counts = { Calls: data.calls.length, Appointments: data.appointments.length, Leads: data.leads.length }

  return (
    <div className="dashboard">
      <div className="dashboard-toolbar">
        <p className="muted small">
          {error ? <span className="error">Refresh failed: {error}</span> : `Updated ${updatedAt?.toLocaleTimeString()}`} ·
          refreshes every 10s
        </p>
        <button className="btn btn-ghost btn-sm" onClick={refresh}>
          Refresh
        </button>
      </div>

      <KpiRow stats={data.stats} />
      <NeedsAttention calls={data.calls} leads={data.leads} onOpenCall={setOpenCallId} />

      <section className="card">
        <div className="tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              className={`tab ${tab === t ? 'tab-active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t} <span className="tab-count">{counts[t]}</span>
            </button>
          ))}
        </div>
        <div className="table-wrap">
          {tab === 'Calls' && <CallsTable calls={data.calls} now={updatedAt} onOpenCall={setOpenCallId} />}
          {tab === 'Appointments' && <AppointmentsTable appointments={data.appointments} />}
          {tab === 'Leads' && <LeadsTable leads={data.leads} />}
        </div>
      </section>

      {openCallId && <CallDetailPanel callId={openCallId} now={updatedAt} onClose={closeCall} />}
    </div>
  )
}
