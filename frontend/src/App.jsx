import React, { useState, createContext, useContext } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import LandingPage from './pages/LandingPage'
import SingleObservation from './pages/SingleObservation'
import MultipleObservations from './pages/MultipleObservations'

const AppContext = createContext()
export const useAppContext = () => useContext(AppContext)

function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [cachedData, setCachedData] = useState({})
  const location = useLocation()

  const isLanding = location.pathname === '/'

  return (
    <AppContext.Provider value={{ cachedData, setCachedData }}>
      <div className="app">
        <Navbar
          onMenuClick={() => setSidebarOpen(!sidebarOpen)}
          isLanding={isLanding}
        />
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className={`main-content ${isLanding ? 'landing' : ''}`}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/single" element={<SingleObservation />} />
            <Route path="/multiple" element={<MultipleObservations />} />
          </Routes>
        </main>
      </div>
    </AppContext.Provider>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AppShell />
    </ThemeProvider>
  )
}
