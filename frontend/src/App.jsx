import { useEffect, useState } from 'react'
import { apiGet } from './lib/api'
import Dashboard from './pages/Dashboard'
import FrontDesk from './pages/FrontDesk'
import QuoteRequest from './pages/QuoteRequest'
import WinBack from './pages/WinBack'

const VIEWS = {
  '#/': 'Front desk',
  '#/quote': 'Get a quote',
  '#/win-back': 'Win-back',
  '#/dashboard': 'Dashboard',
}

function currentView() {
  return VIEWS[window.location.hash] ? window.location.hash : '#/'
}

export default function App() {
  const [view, setView] = useState(currentView)
  const [config, setConfig] = useState(null)
  const [configError, setConfigError] = useState(null)

  useEffect(() => {
    const onHash = () => setView(currentView())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

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
        <nav className="nav" aria-label="Main">
          {Object.entries(VIEWS).map(([hash, label]) => (
            <a key={hash} href={hash} className={`nav-link ${view === hash ? 'nav-active' : ''}`}
               aria-current={view === hash ? 'page' : undefined}>
              {label}
            </a>
          ))}
        </nav>
      </header>

      <main>
        {/* Call pages stay mounted (just hidden) so switching tabs never hangs up a live call. */}
        <div hidden={view !== '#/'}>
          <FrontDesk config={config} configError={configError} />
        </div>
        <div hidden={view !== '#/quote'}>
          <QuoteRequest config={config} />
        </div>
        <div hidden={view !== '#/win-back'}>
          <WinBack config={config} />
        </div>
        {view === '#/dashboard' && <Dashboard />}
      </main>

      <footer className="muted small">Ridgeway Plumbing &amp; Air is a fictional business for demo purposes.</footer>
    </div>
  )
}
