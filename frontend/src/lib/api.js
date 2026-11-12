const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '')

export async function apiGet(path) {
  const res = await fetch(`${API_URL}${path}`)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return body
}
