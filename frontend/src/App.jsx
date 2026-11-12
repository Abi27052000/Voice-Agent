import { useEffect, useState } from 'react'
import CallWidget from './components/CallWidget'
import { apiGet } from './lib/api'

const TRY_SAYING = [
  'My kitchen sink is draining really slowly.',
  "Water is spraying from under my sink!",
  'How much does a water heater replacement cost?',
  'Can someone come out Saturday morning for an AC tune-up?',
]

export default function App() {
  const [config, setConfig] = useState(null)
  const [configError, setConfigError] = useState(null)

  useEffect(() => {
    apiGet('/vapi/config')
      .then(setConfig)
      .catch((err) => setConfigError(err.message))
  }, [])

  return (
    <div className="page">
      <header className="site-header">
        <div className="brand">
          <span className="logo" aria-hidden="true">R</span>
          <div>
            <strong>Ridgeway Plumbing &amp; Air</strong>
            <span className="muted small">AI front-desk demo</span>
          </div>
        </div>
      </header>

      <main className="layout">
        <div>
          {configError ? (
            <section className="card">
              <h2>Backend not reachable</h2>
              <p className="error">{configError}</p>
              <p className="muted">
                Start it with <code>uv run fastapi dev app/main.py</code> in <code>backend/</code>.
              </p>
            </section>
          ) : (
            <CallWidget
              publicKey={config?.public_key}
              assistantId={config?.assistants?.receptionist}
              agentName="Alex"
            />
          )}
        </div>

        <aside className="card">
          <h2>Try saying</h2>
          <ul className="suggestions">
            {TRY_SAYING.map((s) => (
              <li key={s}>“{s}”</li>
            ))}
          </ul>
          <p className="muted small">
            Alex answers like a real receptionist: triages emergencies, collects your details, and logs a
            service request.
          </p>
        </aside>
      </main>

      <footer className="muted small">Ridgeway Plumbing &amp; Air is a fictional business for demo purposes.</footer>
    </div>
  )
}
