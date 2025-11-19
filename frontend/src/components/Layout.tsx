import { Outlet, Link } from 'react-router-dom'
import { useAuthStore } from '../services/authStore'

export default function Layout() {
  const { user, logout } = useAuthStore()

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-primary-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-8">
              <Link to="/" className="text-xl font-bold">
                United Degenerates League
              </Link>
              <Link to="/" className="hover:text-primary-200">
                Dashboard
              </Link>
              <Link to="/competitions" className="hover:text-primary-200">
                Competitions
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm">
                {user?.username}
              </span>
              <button onClick={logout} className="btn btn-secondary text-sm">
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      <footer className="bg-gray-100 border-t border-gray-200 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-600">
          <p>&copy; 2025 United Degenerates League. Mobile-First Design.</p>
        </div>
      </footer>
    </div>
  )
}
