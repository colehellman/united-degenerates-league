// Admin.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Admin from './Admin'
import { useAuthStore } from '../services/authStore'
import api from '../services/api'
import toast from 'react-hot-toast'

vi.mock('../services/authStore', () => ({ useAuthStore: vi.fn() }))
vi.mock('../services/api', () => ({ default: { get: vi.fn(), patch: vi.fn(), delete: vi.fn(), post: vi.fn() } }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const SAMPLE_STATS = {
  total_users: 42,
  active_competitions: 3,
  total_competitions: 10,
  total_picks: 500,
  total_games: 200,
}

const SAMPLE_REPORT = {
  id: 'r1',
  title: 'Layout broken',
  status: 'open',
  category: 'ui',
  description: 'Nav overlaps content',
  created_at: '2026-03-01T00:00:00',
  user: { username: 'alice' },
}

// Report whose status is not in BUG_STATUS_LABELS/BUG_STATUS_COLORS dictionaries —
// exercises the `|| r.status` and `|| ''` fallback branches in the table row.
const REPORT_UNKNOWN_STATUS = {
  id: 'r2',
  title: 'Mystery bug',
  status: 'pending',  // not a known BugReportStatus enum value
  category: 'other',
  description: 'Something weird',
  created_at: '2026-03-01T00:00:00',
  user: { username: 'bob' },
}

const SAMPLE_LOG = {
  id: 'l1',
  action: 'user.login',
  user_id: 'u1',
  created_at: '2026-03-01T00:00:00',
  details: {},
  target_type: 'user',
  target_id: null,
}

// Log with a non-null target_id (exercises `log.target_id ? slice... : '—'` true branch)
// and null details (exercises `log.details ? JSON.stringify(...) : '—'` false branch).
const LOG_WITH_TARGET = {
  id: 'l2',
  action: 'user.ban',
  user_id: 'u1',
  created_at: '2026-03-01T00:00:00',
  details: null,
  target_type: 'user',
  target_id: 'abc123def456789',
}

// ---------------------------------------------------------------------------
// Render helpers
// ---------------------------------------------------------------------------

function defaultApiMock(overrides: {
  bugReports?: any[] | 'loading' | 'error'
  auditLogs?: any[] | 'loading' | 'error'
  stats?: any | 'loading' | 'error'
  users?: any[] | 'loading' | 'error'
  competitions?: any[] | 'loading' | 'error'
} = {}) {
  vi.mocked(api.get).mockImplementation((url: string) => {
    if (url === '/admin/stats') {
      if (overrides.stats === 'loading') return new Promise(() => {})
      if (overrides.stats === 'error') return Promise.reject(new Error('Network error'))
      return Promise.resolve({ data: overrides.stats ?? SAMPLE_STATS })
    }
    if (url === '/admin/users') {
      if (overrides.users === 'loading') return new Promise(() => {})
      if (overrides.users === 'error') return Promise.reject(new Error('Network error'))
      return Promise.resolve({ data: overrides.users ?? [] })
    }
    if (url === '/admin/competitions') {
      if (overrides.competitions === 'loading') return new Promise(() => {})
      if (overrides.competitions === 'error') return Promise.reject(new Error('Network error'))
      return Promise.resolve({ data: overrides.competitions ?? [] })
    }
    if (url === '/bug-reports') {
      if (overrides.bugReports === 'loading') return new Promise(() => {})
      if (overrides.bugReports === 'error') return Promise.reject(new Error('Network error'))
      return Promise.resolve({ data: overrides.bugReports ?? [SAMPLE_REPORT] })
    }
    if (url === '/admin/audit-logs') {
      if (overrides.auditLogs === 'loading') return new Promise(() => {})
      if (overrides.auditLogs === 'error') return Promise.reject(new Error('Network error'))
      return Promise.resolve({ data: overrides.auditLogs ?? [SAMPLE_LOG] })
    }
    return Promise.resolve({ data: [] })
  })
}

/** Standard render with a real user and sample data. */
function renderAdmin(role = 'global_admin') {
  vi.mocked(useAuthStore).mockReturnValue({
    user: { id: '1', username: 'admin', email: 'a@b.com', role, status: 'active' },
  } as any)

  defaultApiMock()

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Admin />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

/** Render with fine-grained control over each tab's response. */
function renderAdminWith(overrides: Parameters<typeof defaultApiMock>[0] = {}) {
  vi.mocked(useAuthStore).mockReturnValue({
    user: { id: '1', username: 'admin', email: 'a@b.com', role: 'global_admin', status: 'active' },
  } as any)

  defaultApiMock(overrides)

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Admin />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

/** Click a tab button by label */
function clickTab(label: string) {
  fireEvent.click(screen.getByRole('button', { name: new RegExp(label, 'i') }))
}

beforeEach(() => vi.clearAllMocks())

// ---------------------------------------------------------------------------
// Access control
// ---------------------------------------------------------------------------

describe('Admin — access control', () => {
  it('redirects non-admin users to /', () => {
    renderAdmin('user')
    // Navigate replaces the component — Admin panel heading should not appear
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Panel rendering
// ---------------------------------------------------------------------------

describe('Admin — panel rendering', () => {
  it('renders the admin panel heading for global_admin', () => {
    renderAdmin()
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
  })

  it('shows bug reports when Bug Reports tab is clicked', async () => {
    renderAdmin()
    clickTab('Bug Reports')
    // Text appears in both desktop table and mobile card views
    const matches = await screen.findAllByText('Layout broken')
    expect(matches.length).toBeGreaterThan(0)
  })

  it('switches to audit logs tab when clicked', async () => {
    renderAdmin()
    clickTab('Audit Logs')
    const matches = await screen.findAllByText('user.login')
    expect(matches.length).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// Bug reports — status badge
// ---------------------------------------------------------------------------

describe('Admin — bug report status badge', () => {
  it('shows Open badge for an open report', async () => {
    renderAdmin()
    clickTab('Bug Reports')
    await screen.findAllByText('Layout broken')
    expect(screen.getAllByText('Open').length).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// Bug reports — loading & empty states
// ---------------------------------------------------------------------------

describe('Admin — bug reports loading, empty, and error states', () => {
  it('shows spinner while bug reports are fetching', () => {
    renderAdminWith({ bugReports: 'loading' })
    clickTab('Bug Reports')
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows empty-state message when there are no bug reports', async () => {
    renderAdminWith({ bugReports: [] })
    clickTab('Bug Reports')
    await screen.findByText(/no bug reports submitted yet/i)
  })

  it('shows error state instead of empty state when bug reports fetch fails', async () => {
    renderAdminWith({ bugReports: 'error' })
    clickTab('Bug Reports')
    await screen.findByText(/failed to load bug reports/i)
    expect(screen.queryByText(/no bug reports submitted yet/i)).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Status update mutation
// ---------------------------------------------------------------------------

describe('Admin — status update mutation', () => {
  it('calls api.patch with the new status when the select changes', async () => {
    vi.mocked(api.patch).mockResolvedValueOnce({ data: {} })
    renderAdmin()
    clickTab('Bug Reports')

    await screen.findAllByText('Layout broken')
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'resolved' } })

    await waitFor(() => {
      expect(api.patch).toHaveBeenCalledWith('/bug-reports/r1', { status: 'resolved' })
    })
  })

  it('shows success toast after a successful status update', async () => {
    vi.mocked(api.patch).mockResolvedValueOnce({ data: {} })
    renderAdmin()
    clickTab('Bug Reports')

    await screen.findAllByText('Layout broken')
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'resolved' } })

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Status updated')
    })
  })

  it('shows error toast when status update fails', async () => {
    vi.mocked(api.patch).mockRejectedValueOnce(new Error('Server error'))
    renderAdmin()
    clickTab('Bug Reports')

    await screen.findAllByText('Layout broken')
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'resolved' } })

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to update status')
    })
  })
})

// ---------------------------------------------------------------------------
// Audit logs — loading & empty states
// ---------------------------------------------------------------------------

describe('Admin — audit logs loading, empty, and error states', () => {
  it('shows spinner while audit logs are fetching', () => {
    renderAdminWith({ auditLogs: 'loading' })
    clickTab('Audit Logs')
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows empty-state message when there are no audit logs', async () => {
    renderAdminWith({ auditLogs: [] })
    clickTab('Audit Logs')
    await screen.findByText(/no audit log entries yet/i)
  })

  it('shows error state instead of empty state when audit logs fetch fails', async () => {
    renderAdminWith({ auditLogs: 'error' })
    clickTab('Audit Logs')
    await screen.findByText(/failed to load audit logs/i)
    expect(screen.queryByText(/no audit log entries yet/i)).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Branch-coverage edge cases
// ---------------------------------------------------------------------------

describe('Admin — bug report table edge cases', () => {
  it('shows raw status string for an unknown status value', async () => {
    // Exercises `BUG_STATUS_LABELS[r.status] || r.status` and
    // `BUG_STATUS_COLORS[r.status] || ''` fallback branches.
    renderAdminWith({ bugReports: [REPORT_UNKNOWN_STATUS] })
    clickTab('Bug Reports')
    await screen.findAllByText('Mystery bug')
    // 'pending' is not a key in BUG_STATUS_LABELS — raw value is displayed
    expect(screen.getAllByText('pending').length).toBeGreaterThan(0)
  })
})

describe('Admin — audit log table edge cases', () => {
  it('shows truncated target_id and dash for null details', async () => {
    // LOG_WITH_TARGET: target_id truthy → truncated form; details null → '—'
    // SAMPLE_LOG: target_id null → '—'; details {} → '{}' (JSON)
    renderAdminWith({ auditLogs: [SAMPLE_LOG, LOG_WITH_TARGET] })
    clickTab('Audit Logs')
    await screen.findAllByText('user.ban')
    // target_id 'abc123def456789' sliced to 8 chars
    expect(screen.getAllByText('abc123de').length).toBeGreaterThan(0)
  })
})
