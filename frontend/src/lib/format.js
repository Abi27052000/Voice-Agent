const usd0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
const usd2 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 3 })

export const money = (n) => (n == null ? '—' : usd0.format(n))
export const cents = (n) => (n == null ? '—' : usd2.format(n))
export const percent = (r) => (r == null ? '—' : `${Math.round(r * 100)}%`)

export function duration(seconds) {
  if (seconds == null) return '—'
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return m ? `${m}m ${String(s).padStart(2, '0')}s` : `${s}s`
}

export function dateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

export function phone(digits) {
  if (!digits) return '—'
  if (digits.length === 10) return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`
  if (digits.length === 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`
  return digits
}

/** "maintenance_tuneup" -> "Maintenance tuneup", "customer-ended-call" -> "Customer ended call" */
export function humanize(value) {
  if (!value) return '—'
  const text = value.replace(/[_-]+/g, ' ').trim()
  return text.charAt(0).toUpperCase() + text.slice(1)
}
