import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './services/authStore'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import Competitions from './pages/Competitions'
import CompetitionDetail from './pages/CompetitionDetail'
import CreateCompetition from './pages/CreateCompetition'
import Admin from './pages/Admin'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  const { isAuthenticated, isInitializing, checkAuth } = useAuthStore()

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
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500 text-sm">Loading…</p>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={isAuthenticated ? <Navigate to="/" /> : <Login />} />
        <Route path="/register" element={isAuthenticated ? <Navigate to="/" /> : <Register />} />

        <Route element={<Layout />}>
          <Route path="/" element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} />
          <Route path="/competitions" element={isAuthenticated ? <Competitions /> : <Navigate to="/login" />} />
          <Route path="/competitions/create" element={isAuthenticated ? <CreateCompetition /> : <Navigate to="/login" />} />
          <Route path="/competitions/:id" element={isAuthenticated ? <CompetitionDetail /> : <Navigate to="/login" />} />
          <Route path="/admin" element={isAuthenticated ? <Admin /> : <Navigate to="/login" />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}

export default App
