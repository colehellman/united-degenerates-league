// Layout.test.tsx

import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './Layout'

// BugReportModal calls useMutation so we need a QueryClientProvider wrapper.
// We do NOT mock BugReportModal — the open/close cycle exercises the real
// onClose handler (`() => setShowBugReport(false)`) in Layout.
vi.mock('../services/api', () => ({
  default: { post: vi.fn() },
}))

// Mutable so individual tests can override the role without re-mocking.
let mockUser: { username: string; role?: string } = { username: 'testuser', role: 'user' }
const mockLogout = vi.fn()

vi.mock('../services/authStore', () => ({
  useAuthStore: () => ({
    user: mockUser,
    logout: mockLogout,
  }),
}))

function renderLayout() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  // Reset to a plain non-admin user before each test.
  mockUser = { username: 'testuser', role: 'user' }
})

describe('Layout — navigation', () => {
  it('renders brand link, nav links, user info, and action buttons', () => {
    renderLayout()
    // Brand link: full name in a hidden-sm span, abbreviated "UDL" in another.
    // getByText matches the specific span text, not the combined Link text.
    expect(screen.getByText('United Degenerates League')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Competitions')).toBeInTheDocument()
    // Username renders in both the desktop nav and mobile top-bar (CSS hides
    // one at runtime, but in jsdom both spans are in the DOM simultaneously).
    expect(screen.getAllByText('testuser').length).toBeGreaterThan(0)
    expect(screen.getByRole('main')).toBeInTheDocument()
    // Desktop-only "Report a Bug" and "Logout" buttons; mobile dropdown only
    // appears when the hamburger is clicked, so both have single matches here.
    expect(screen.getByRole('button', { name: /report a bug/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })

  it('shows Admin ★ link for global_admin role', () => {
    mockUser = { username: 'admin', role: 'global_admin' }
    renderLayout()
    // Only the desktop Admin ★ link is in the DOM (mobile dropdown is closed).
    expect(screen.getByText(/Admin ★/)).toBeInTheDocument()
  })

  it('hides Admin ★ link for non-admin role', () => {
    renderLayout()
    expect(screen.queryByText(/Admin ★/)).not.toBeInTheDocument()
  })
})

describe('Layout — logout', () => {
  it('calls logout when Logout button is clicked', () => {
    renderLayout()
    // Desktop Logout button — the only one visible when mobile menu is closed.
    fireEvent.click(screen.getByRole('button', { name: /logout/i }))
    expect(mockLogout).toHaveBeenCalledTimes(1)
  })
})

describe('Layout — mobile menu aria-expanded', () => {
  it('hamburger starts with aria-expanded="false"', () => {
    renderLayout()
    const hamburger = screen.getByRole('button', { name: /toggle menu/i })
    expect(hamburger).toHaveAttribute('aria-expanded', 'false')
  })

  it('hamburger sets aria-expanded="true" after click', () => {
    renderLayout()
    const hamburger = screen.getByRole('button', { name: /toggle menu/i })
    fireEvent.click(hamburger)
    expect(hamburger).toHaveAttribute('aria-expanded', 'true')
  })
})

describe('Layout — active nav link on sub-routes', () => {
  it('marks Competitions link as current page when on a sub-route', () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/competitions/abc-123']}>
          <Layout />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    // Both desktop and mobile links rendered; find by aria-current
    const currentLinks = screen.getAllByRole('link', { name: /competitions/i }).filter(
      (el) => el.getAttribute('aria-current') === 'page',
    )
    expect(currentLinks.length).toBeGreaterThan(0)
  })

  it('does not mark Dashboard as current when navigated to a sub-route', () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/competitions/abc-123']}>
          <Layout />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const dashLinks = screen.getAllByRole('link', { name: /dashboard/i })
    dashLinks.forEach((link) => {
      expect(link).not.toHaveAttribute('aria-current', 'page')
    })
  })
})

describe('Layout — bug report modal', () => {
  it('opens the modal when Report a Bug is clicked', () => {
    renderLayout()
    // Title input only exists inside the modal form
    expect(screen.queryByLabelText(/title/i)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /report a bug/i }))
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument()
  })

  it('closes the modal when Cancel is clicked inside the modal', () => {
    renderLayout()
    // Open the modal
    fireEvent.click(screen.getByRole('button', { name: /report a bug/i }))
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument()
    // Cancel button lives inside the modal — clicking it calls onClose
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    // Form fields disappear once the modal is closed
    expect(screen.queryByLabelText(/title/i)).not.toBeInTheDocument()
  })
})
