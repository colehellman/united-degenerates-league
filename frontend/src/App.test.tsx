// App.test.tsx
//
// Tests the auth initialization contract documented in authStore.test.ts,
// now at the routing level. These guard against:
//
//   • Showing the login page on every hard refresh (flash of unauthenticated)
//   • Routing to "/" before checkAuth resolves (flicker or premature redirect)
//   • checkAuth never being called (Zustand has no persistence — store always
//     resets to isAuthenticated: false on load, so checkAuth is required)

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { useAuthStore } from './services/authStore'

vi.mock('./services/authStore', () => ({
  useAuthStore: vi.fn(),
}))

// Page components are heavy; stub them to isolate App routing logic.
vi.mock('./pages/Dashboard', () => ({ default: () => <div>Dashboard</div> }))
vi.mock('./pages/Login', () => ({ default: () => <div>Login</div> }))
vi.mock('./pages/Register', () => ({ default: () => <div>Register</div> }))
vi.mock('./pages/Competitions', () => ({ default: () => <div>Competitions</div> }))
vi.mock('./pages/CompetitionDetail', () => ({ default: () => <div>CompetitionDetail</div> }))
vi.mock('./pages/CreateCompetition', () => ({ default: () => <div>CreateCompetition</div> }))
vi.mock('./pages/Admin', () => ({ default: () => <div>Admin</div> }))
vi.mock('./components/Layout', async () => {
  // vi.importActual is the Vitest-idiomatic way to access real module exports
  // inside a mock factory without using require() (which ESLint bans in ESM).
  const { Outlet } = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    default: () => <Outlet />,
  }
})
vi.mock('./components/ErrorBoundary', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

const checkAuth = vi.fn()

function buildStore(overrides: object) {
  return {
    isAuthenticated: false,
    isInitializing: false,
    user: null,
    checkAuth,
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    ...overrides,
  }
}

function renderApp(initialPath = '/') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  checkAuth.mockClear()
})

describe('App — loading screen', () => {
  it('renders a loading indicator while isInitializing is true', () => {
    vi.mocked(useAuthStore).mockReturnValue(
      buildStore({ isInitializing: true, isAuthenticated: false }),
    )
    renderApp()
    // Must not render any route content while cookie validation is pending.
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
    expect(screen.queryByText('Login')).not.toBeInTheDocument()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
  })

  it('calls checkAuth on mount so cookie is validated after every hard refresh', () => {
    vi.mocked(useAuthStore).mockReturnValue(
      buildStore({ isInitializing: true }),
    )
    renderApp()
    // Zustand has no persistence — without this call, isAuthenticated stays
    // false even for users with valid session cookies.
    expect(checkAuth).toHaveBeenCalledTimes(1)
  })
})

describe('App — unauthenticated routing', () => {
  beforeEach(() => {
    vi.mocked(useAuthStore).mockReturnValue(
      buildStore({ isAuthenticated: false, isInitializing: false }),
    )
  })

  it('renders Login page at /login', () => {
    renderApp('/login')
    expect(screen.getByText('Login')).toBeInTheDocument()
  })

  it('redirects / to /login when not authenticated', () => {
    renderApp('/')
    expect(screen.getByText('Login')).toBeInTheDocument()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
  })
})

describe('App — authenticated routing', () => {
  beforeEach(() => {
    vi.mocked(useAuthStore).mockReturnValue(
      buildStore({ isAuthenticated: true, isInitializing: false }),
    )
  })

  it('renders Dashboard at / when authenticated', () => {
    renderApp('/')
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('redirects /login to / when already authenticated', () => {
    renderApp('/login')
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.queryByText('Login')).not.toBeInTheDocument()
  })

  it('redirects /register to / when already authenticated', () => {
    renderApp('/register')
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.queryByText('Register')).not.toBeInTheDocument()
  })
})
