import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './services/authStore'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import Competitions from './pages/Competitions'
import CompetitionDetail from './pages/CompetitionDetail'
import Layout from './components/Layout'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" /> : <Login />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/" /> : <Register />} />

      <Route element={<Layout />}>
        <Route path="/" element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />} />
        <Route path="/competitions" element={isAuthenticated ? <Competitions /> : <Navigate to="/login" />} />
        <Route path="/competitions/:id" element={isAuthenticated ? <CompetitionDetail /> : <Navigate to="/login" />} />
      </Route>
    </Routes>
  )
}

export default App
