import CallWidget from '../components/CallWidget'

const TRY_SAYING = [
  'My kitchen sink is draining really slowly.',
  'Water is spraying from under my sink!',
  'How much does a water heater replacement cost?',
  'Can someone come out Saturday morning for an AC tune-up?',
]

export default function FrontDesk({ config, configError }) {
  return (
    <div className="layout">
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
          Alex triages emergencies, checks the live schedule, and books a real arrival window. Every call
          then shows up on the dashboard with a summary and outcome.
        </p>
      </aside>
    </div>
  )
}
