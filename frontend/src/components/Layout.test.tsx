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
    expect(screen.getByText('United Degenerates League')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Competitions')).toBeInTheDocument()
    expect(screen.getByText('testuser')).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /report a bug/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })

  it('shows Admin ★ link for global_admin role', () => {
    mockUser = { username: 'admin', role: 'global_admin' }
    renderLayout()
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
    fireEvent.click(screen.getByRole('button', { name: /logout/i }))
    expect(mockLogout).toHaveBeenCalledTimes(1)
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
