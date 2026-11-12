// Status is never color alone: every tone carries an icon glyph and a text label.
const ICONS = { good: '✓', warning: '!', critical: '▲', neutral: '•', info: 'i' }

export default function Badge({ tone = 'neutral', children }) {
  return (
    <span className={`badge badge-${tone}`}>
      <span className="badge-icon" aria-hidden="true">
        {ICONS[tone]}
      </span>
      {children}
    </span>
  )
}

// Vapi usually finishes extraction within a minute of the call ending.
const ANALYSIS_GRACE_MS = 3 * 60 * 1000

function callEndedAt(call) {
  if (!call.started_at) return null
  return new Date(call.started_at).getTime() + (call.duration_seconds ?? 0) * 1000
}

/** The badges that summarize one call's outcome. `now` is a Date from the last data refresh. */
export function CallOutcomeBadges({ call, now }) {
  if (call.outcome_status !== 'ready') {
    const endedAt = callEndedAt(call)
    const stale = now && endedAt && now.getTime() - endedAt > ANALYSIS_GRACE_MS
    return <Badge>{stale ? 'Not analyzed' : 'Analyzing…'}</Badge>
  }
  return (
    <span className="badge-row">
      {call.booked ? <Badge tone="good">Booked</Badge> : <Badge>Not booked</Badge>}
      {call.urgency === 'emergency' && <Badge tone="critical">Emergency</Badge>}
      {call.follow_up_needed && <Badge tone="warning">Follow-up</Badge>}
    </span>
  )
}

const LEAD_TONES = { booked: 'good', emergency: 'critical', new: 'info', contacted: 'neutral' }

export function LeadStatusBadge({ status }) {
  const label = status.charAt(0).toUpperCase() + status.slice(1)
  return <Badge tone={LEAD_TONES[status] ?? 'neutral'}>{label}</Badge>
}
