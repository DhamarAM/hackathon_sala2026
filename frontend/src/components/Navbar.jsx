import { Link, useLocation } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'

export default function Navbar({ onMenuClick, isLanding }) {
  const location = useLocation()
  const { theme, toggleTheme } = useTheme()

  return (
    <nav className="navbar">
      <div className="navbar-left">
        <button className="menu-btn" onClick={onMenuClick} aria-label="Menu">
          &#9776;
        </button>
        {!isLanding && (
          <>
            <Link to="/single" className={`nav-link ${location.pathname === '/single' ? 'active' : ''}`}>
              Single Analysis
            </Link>
            <Link to="/multiple" className={`nav-link ${location.pathname === '/multiple' ? 'active' : ''}`}>
              Batch Report
            </Link>
          </>
        )}
      </div>
      <div className="navbar-right">
        <button className="theme-toggle" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
          {theme === 'dark' ? '\u2600' : '\u263E'}
        </button>
        <Link to="/" className="logo">Dragon Ocean Analyzer</Link>
      </div>
    </nav>
  )
}
