// App.test.tsx — routing contract
//
// Verifies that authenticated and unauthenticated users are sent to the
// correct routes. All page components are stubbed so the tests stay fast
// and isolated to App's routing logic.

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { useAuthStore } from './services/authStore'

vi.mock('./services/authStore', () => ({ useAuthStore: vi.fn() }))

vi.mock('./pages/Dashboard', () => ({ default: () => <div>Dashboard</div> }))
vi.mock('./pages/Login', () => ({ default: () => <div>Login</div> }))
vi.mock('./pages/Register', () => ({ default: () => <div>Register</div> }))
vi.mock('./pages/Competitions', () => ({ default: () => <div>Competitions</div> }))
vi.mock('./pages/CompetitionDetail', () => ({ default: () => <div>CompetitionDetail</div> }))
vi.mock('./pages/CreateCompetition', () => ({ default: () => <div>CreateCompetition</div> }))
vi.mock('./pages/Admin', () => ({ default: () => <div>Admin</div> }))
vi.mock('./components/Layout', async () => {
  const { Outlet } = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { default: () => <Outlet /> }
})
vi.mock('./components/ErrorBoundary', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

function renderApp(initialPath = '/') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  vi.mocked(useAuthStore).mockReturnValue({
    isAuthenticated: false,
    isInitializing: false,
    user: null,
    checkAuth: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    ...currentStore,
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

let currentStore: Partial<ReturnType<typeof useAuthStore>> = {}

beforeEach(() => {
  currentStore = {}
})

describe('App — unauthenticated routing', () => {
  it('shows Login at /login', () => {
    currentStore = { isAuthenticated: false }
    renderApp('/login')
    expect(screen.getByText('Login')).toBeInTheDocument()
  })

  it('redirects / to /login when not authenticated', () => {
    currentStore = { isAuthenticated: false }
    renderApp('/')
    expect(screen.getByText('Login')).toBeInTheDocument()
  })

  it('redirects /competitions to /login when not authenticated', () => {
    currentStore = { isAuthenticated: false }
    renderApp('/competitions')
    expect(screen.getByText('Login')).toBeInTheDocument()
  })
})

describe('App — authenticated routing', () => {
  beforeEach(() => {
    currentStore = { isAuthenticated: true }
  })

  it('renders Dashboard at /', () => {
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
  })

  it('renders Competitions at /competitions', () => {
    renderApp('/competitions')
    expect(screen.getByText('Competitions')).toBeInTheDocument()
  })

  it('renders Admin at /admin', () => {
    renderApp('/admin')
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })
})
