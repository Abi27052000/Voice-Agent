const FEATURES = [
  {
    title: 'AI receptionist that books jobs',
    outcome: 'Never miss a call',
    body: 'Alex answers 24/7, checks the live schedule, books a real arrival window, and reads back a reference number. Emergencies are handed to Jordan, a dispatcher agent who keeps the caller safe and alerts the on-call tech.',
    proof: 'Squad handoff · booking tools · emergency triage',
    href: '#/front-desk',
    cta: 'Talk to Alex',
  },
  {
    title: 'Instant lead follow-up',
    outcome: 'Call new leads back in seconds',
    body: "When someone requests a quote, Sam calls them back right away, already knowing their name and problem, and books the visit while they're still interested.",
    proof: 'Form → call placed in under a second · consent required',
    href: '#/quote',
    cta: 'Request a quote',
  },
  {
    title: 'Dead-lead reactivation',
    outcome: 'Turn old customers into booked jobs',
    body: "Taylor calls past customers with a seasonal offer, books the ones who are interested, and records every outcome. Do-not-call requests are honored instantly and never re-dialed.",
    proof: 'Opt-out handling · voicemail · campaign-ready CSV export',
    href: '#/win-back',
    cta: 'Run the win-back',
  },
  {
    title: 'AI-powered CRM',
    outcome: 'See what every call was worth',
    body: 'Every call is summarized and scored automatically: booked or not, urgency, job type, sentiment, and what staff should follow up on, with booking rate, revenue, and speed-to-lead KPIs.',
    proof: 'Structured outputs · live dashboard',
    href: '#/dashboard',
    cta: 'Open the dashboard',
  },
]

const TRUST = [
  {
    title: 'Tested like software',
    body: 'Vapi Simulations play realistic callers (stressed, skeptical, cooperative) against the real agents: 8 scenarios, 21 checks, all passing. Plus 57 backend tests.',
  },
  {
    title: 'Safe by design',
    body: 'The AI never gets to choose whose record it changes. Tool calls are validated on the server, consent is required before calling, and customer data never leaves the local network.',
  },
  {
    title: 'Numbers from facts, not guesses',
    body: 'A call only counts as booked if an appointment exists in the CRM. AI extraction adds context but never inflates the booking rate or revenue.',
  },
]

const FLOW = [
  { label: 'Caller', detail: 'Phone or browser' },
  { label: 'Vapi voice agents', detail: 'Deepgram speech-to-text · GPT-4.1 mini · Vapi voices' },
  { label: 'FastAPI webhook', detail: 'Authenticated tools: availability, booking, leads' },
  { label: 'CRM database', detail: 'Leads, appointments, call outcomes' },
  { label: 'Dashboard', detail: 'KPIs, follow-ups, transcripts' },
]

const STACK = [
  'Vapi assistants',
  'Squads & handoffs',
  'Function tools',
  'Structured outputs',
  'Simulations',
  'Campaign export',
  'Python · FastAPI',
  'SQLAlchemy',
  'React · Vite',
  'Vapi Web SDK',
]

export default function Home() {
  return (
    <div className="home">
      <section className="hero">
        <p className="eyebrow">Live demo · Ridgeway Plumbing &amp; Air (fictional)</p>
        <h1>An AI front desk for local service businesses</h1>
        <p className="hero-lede">
          It answers every call, books jobs into the schedule, calls new leads back in seconds, wins back old
          customers, and shows the owner exactly what it's worth.
        </p>
        <div className="hero-actions">
          <a className="btn btn-primary" href="#/front-desk">
            Talk to the AI receptionist
          </a>
          <a className="btn btn-ghost" href="#/dashboard">
            See the dashboard
          </a>
        </div>
        <p className="muted small">Calls run in your browser with your microphone. No phone number needed.</p>
      </section>

      <section aria-labelledby="features-title">
        <h2 id="features-title" className="section-title">
          What it does
        </h2>
        <div className="feature-grid">
          {FEATURES.map((f) => (
            <article key={f.title} className="card feature">
              <p className="eyebrow">{f.outcome}</p>
              <h3>{f.title}</h3>
              <p>{f.body}</p>
              <p className="muted small">{f.proof}</p>
              <a className="feature-link" href={f.href}>
                {f.cta} →
              </a>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="trust-title">
        <h2 id="trust-title" className="section-title">
          Built to be trusted with real customers
        </h2>
        <div className="trust-grid">
          {TRUST.map((t) => (
            <div key={t.title} className="card">
              <h3>{t.title}</h3>
              <p className="muted">{t.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="arch-title" className="card">
        <h2 id="arch-title" className="section-title">
          How it's built
        </h2>
        <ol className="flow" aria-label="Request flow">
          {FLOW.map((step, i) => (
            <li key={step.label} className="flow-step">
              <span className="flow-index" aria-hidden="true">
                {i + 1}
              </span>
              <strong>{step.label}</strong>
              <span className="muted small">{step.detail}</span>
            </li>
          ))}
        </ol>
        <p className="muted small">
          Assistants, tools, the squad, and post-call extraction are defined in code and synced to Vapi with one
          idempotent script, so the whole setup is reviewable and reproducible.
        </p>
        <ul className="chips" aria-label="Technology">
          {STACK.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
