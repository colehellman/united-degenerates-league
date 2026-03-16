import { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation, useSearchParams } from 'react-router-dom'
import { useAuthStore } from './services/authStore'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import Competitions from './pages/Competitions'
import CompetitionDetail from './pages/CompetitionDetail'
import CreateCompetition from './pages/CreateCompetition'
import Admin from './pages/Admin'
import InviteLanding from './pages/InviteLanding'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'

function NotFound() {
  return (
    <div className="text-center py-16">
      <h2 className="text-4xl font-bold text-gray-900 mb-2">404</h2>
      <p className="text-gray-600 mb-6">Page not found</p>
      <a href="/" className="btn btn-primary">Go to Dashboard</a>
    </div>
  )
}

function App() {
  const { isAuthenticated, isInitializing, checkAuth } = useAuthStore()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const redirectParam = (() => {
    const r = searchParams.get('redirect')
    return r && r.startsWith('/') && !r.startsWith('//') ? r : null
  })()

  useEffect(() => {
    // Validate the httpOnly cookie on every app load. Without this, refreshing
    // the page always sees isAuthenticated: false (Zustand has no persistence),
    // even when the user has a valid session — forcing an unnecessary re-login.
    checkAuth()
  // Zustand actions are stable references — this won't cause re-runs, but the
  // linter requires the dep to be listed explicitly.
  }, [checkAuth])

  // Block routing decisions until we know whether the cookie is valid.
  // This prevents a flash of the login page for already-authenticated users.
  if (isInitializing) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-gray-50">
        <svg
          className="animate-spin h-8 w-8 text-primary-600"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p className="text-gray-500 text-sm">Connecting…</p>
      </div>
    )
  }

  return (
    <ErrorBoundary resetKey={location.pathname}>
      <Routes>
        <Route path="/login" element={isAuthenticated ? <Navigate to={redirectParam || "/"} /> : <Login />} />
        <Route path="/register" element={isAuthenticated ? <Navigate to={redirectParam || "/"} /> : <Register />} />

        <Route path="/invite/:token" element={<InviteLanding />} />

        <Route element={<Layout />}>
          <Route path="/" element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} />
          <Route path="/competitions" element={isAuthenticated ? <Competitions /> : <Navigate to="/login" />} />
          <Route path="/competitions/create" element={isAuthenticated ? <CreateCompetition /> : <Navigate to="/login" />} />
          <Route path="/competitions/:id" element={isAuthenticated ? <CompetitionDetail /> : <Navigate to="/login" />} />
          <Route path="/admin" element={isAuthenticated ? <Admin /> : <Navigate to="/login" />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}

export default App
