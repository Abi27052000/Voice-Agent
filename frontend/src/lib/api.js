const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '')

function describeDetail(detail, status) {
  if (!detail) return `Request failed (${status})`
  if (typeof detail === 'string') return detail
  // FastAPI validation errors: [{ loc: [...], msg }]
  if (Array.isArray(detail)) return detail.map((d) => `${d.loc?.slice(-1)[0] ?? 'field'}: ${d.msg}`).join('; ')
  return JSON.stringify(detail)
}

async function request(path, options) {
  const res = await fetch(`${API_URL}${path}`, options)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(describeDetail(body.detail, res.status))
  }
  return body
}

export const apiGet = (path) => request(path)

export const apiPost = (path, data) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
