import { Link, useLocation } from 'react-router-dom'

export default function Sidebar({ isOpen, onClose }) {
  const location = useLocation()

  const links = [
    { to: '/', icon: '\u2302', label: 'Home' },
    { to: '/single', icon: '\u266A', label: 'Single Observation' },
    { to: '/multiple', icon: '\u2630', label: 'Multiple Observations' },
  ]

  return (
    <>
      <div className={`sidebar-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <span className="logo">Dragon Ocean Analyzer</span>
          <button className="menu-btn" onClick={onClose}>&#10005;</button>
        </div>
        {links.map(({ to, icon, label }) => (
          <Link
            key={to}
            to={to}
            className={`sidebar-link ${location.pathname === to ? 'active' : ''}`}
            onClick={onClose}
          >
            <span className="sidebar-link-icon">{icon}</span>
            {label}
          </Link>
        ))}
        <div style={{ flex: 1 }} />
        <div style={{ padding: '16px 0', borderTop: '1px solid var(--surface-border)', fontSize: 12, color: 'var(--text-dim)' }}>
          Galapagos Marine Reserve<br />Acoustic Monitoring Platform
        </div>
      </aside>
    </>
  )
}
