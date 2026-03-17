import { useState, useEffect } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../services/authStore'
import { useThemeStore } from '../services/themeStore'
import BugReportModal from './BugReportModal'

export default function Layout() {
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const [showBugReport, setShowBugReport] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()

  const closeMobileMenu = () => setMobileMenuOpen(false)

  // Close mobile menu on any route change (covers programmatic navigation)
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname])

  // Exact match for '/' (Dashboard) so it doesn't highlight on every sub-route.
  // All other links use startsWith so /competitions/123 keeps Competitions active.
  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)

  const navLinkProps = (path: string) => ({
    className: `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive(path) ? 'bg-primary-700 text-white' : 'text-primary-100 hover:bg-primary-700 hover:text-white'
    }`,
    ...(isActive(path) ? { 'aria-current': 'page' as const } : {}),
  })

  return (
    <div className="min-h-screen flex flex-col">
      <BugReportModal isOpen={showBugReport} onClose={() => setShowBugReport(false)} />

      <nav className="bg-primary-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Top bar */}
          <div className="flex justify-between items-center h-14 sm:h-16">
            {/* Logo */}
            <Link
              to="/"
              className="font-bold text-white shrink-0 text-sm sm:text-base md:text-lg lg:text-xl"
              onClick={closeMobileMenu}
            >
              <span className="hidden sm:inline">United Degenerates League</span>
              <span className="sm:hidden">UDL</span>
            </Link>

            {/* Desktop nav links */}
            <div className="hidden md:flex items-center space-x-1">
              <Link to="/" {...navLinkProps('/')}>Dashboard</Link>
              <Link to="/competitions" {...navLinkProps('/competitions')}>Competitions</Link>
              {user?.role === 'global_admin' && (
                <Link to="/admin" className="block px-3 py-2 rounded-md text-sm font-medium text-yellow-200 hover:bg-primary-700 transition-colors">
                  Admin ★
                </Link>
              )}
            </div>

            {/* Desktop right actions */}
            <div className="hidden md:flex items-center space-x-3">
              <span className="text-sm text-primary-200 truncate max-w-[120px]">{user?.username}</span>
              <button
                onClick={toggleTheme}
                aria-label="Toggle dark mode"
                className="p-2 rounded-md text-primary-100 hover:bg-primary-700 transition-colors"
              >
                {theme === 'dark' ? (
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                ) : (
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                )}
              </button>
              <button
                onClick={() => setShowBugReport(true)}
                className="btn btn-secondary text-sm py-1.5"
              >
                Report a Bug
              </button>
              <button onClick={() => logout()} className="btn btn-secondary text-sm py-1.5">
                Logout
              </button>
            </div>

            {/* Mobile: username + hamburger */}
            <div className="flex md:hidden items-center gap-3">
              <span className="text-sm text-primary-200 truncate max-w-[80px]">{user?.username}</span>
              <button
                onClick={() => setMobileMenuOpen((o) => !o)}
                aria-label="Toggle menu"
                aria-expanded={mobileMenuOpen}
                className="p-2 rounded-md text-primary-100 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
              >
                {/* Hamburger / X icon */}
                {mobileMenuOpen ? (
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                ) : (
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile dropdown menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-primary-500 bg-primary-700 px-4 py-3 space-y-1">
            <Link to="/" {...navLinkProps('/')} onClick={closeMobileMenu}>
              Dashboard
            </Link>
            <Link to="/competitions" {...navLinkProps('/competitions')} onClick={closeMobileMenu}>
              Competitions
            </Link>
            {user?.role === 'global_admin' && (
              <Link
                to="/admin"
                className="block px-3 py-2 rounded-md text-sm font-medium text-yellow-200 hover:bg-primary-600 transition-colors"
                onClick={closeMobileMenu}
              >
                Admin ★
              </Link>
            )}
            <div className="border-t border-primary-600 pt-3 mt-2 space-y-1">
              <button
                onClick={() => { toggleTheme(); closeMobileMenu() }}
                className="w-full text-left px-3 py-2 rounded-md text-sm font-medium text-primary-100 hover:bg-primary-600 transition-colors"
              >
                {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
              </button>
              <button
                onClick={() => { setShowBugReport(true); closeMobileMenu() }}
                className="w-full text-left px-3 py-2 rounded-md text-sm font-medium text-primary-100 hover:bg-primary-600 transition-colors"
              >
                Report a Bug
              </button>
              <button
                onClick={() => { logout(); closeMobileMenu() }}
                className="w-full text-left px-3 py-2 rounded-md text-sm font-medium text-primary-100 hover:bg-primary-600 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        )}
      </nav>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>

      <footer className="bg-gray-100 border-t border-gray-200 py-4 dark:bg-gray-800 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 text-center text-sm text-gray-600 dark:text-gray-400">
          &copy; {new Date().getFullYear()} United Degenerates League
        </div>
      </footer>
    </div>
  )
}
