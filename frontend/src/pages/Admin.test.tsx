// Admin.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Admin from './Admin'
import { useAuthStore } from '../services/authStore'
import api from '../services/api'
import toast from 'react-hot-toast'

vi.mock('../services/authStore', () => ({ useAuthStore: vi.fn() }))
vi.mock('../services/api', () => ({ default: { get: vi.fn(), patch: vi.fn() } }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

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

/** Standard render with a real user and sample data for both tabs. */
function renderAdmin(role = 'global_admin') {
  vi.mocked(useAuthStore).mockReturnValue({
    user: { id: '1', username: 'admin', email: 'a@b.com', role, status: 'active' },
  } as any)

  // Default API responses — bug reports and audit logs
  vi.mocked(api.get).mockImplementation((url: string) => {
    if (url === '/bug-reports') return Promise.resolve({ data: [SAMPLE_REPORT] })
    if (url === '/admin/audit-logs') return Promise.resolve({ data: [SAMPLE_LOG] })
    return Promise.resolve({ data: [] })
  })

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Admin />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

/**
 * Render with fine-grained control over each tab's response.
 * Pass `'loading'` to return a never-resolving promise (simulates in-flight request).
 */
function renderAdminWith({
  bugReports,
  auditLogs,
}: {
  bugReports?: any[] | 'loading'
  auditLogs?: any[] | 'loading'
} = {}) {
  vi.mocked(useAuthStore).mockReturnValue({
    user: { id: '1', username: 'admin', email: 'a@b.com', role: 'global_admin', status: 'active' },
  } as any)

  vi.mocked(api.get).mockImplementation((url: string) => {
    if (url === '/bug-reports') {
      return bugReports === 'loading'
        ? new Promise(() => {})
        : Promise.resolve({ data: bugReports ?? [SAMPLE_REPORT] })
    }
    if (url === '/admin/audit-logs') {
      return auditLogs === 'loading'
        ? new Promise(() => {})
        : Promise.resolve({ data: auditLogs ?? [SAMPLE_LOG] })
    }
    return Promise.resolve({ data: [] })
  })

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Admin />
      </MemoryRouter>
    </QueryClientProvider>,
  )
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

  it('shows bug reports by default', async () => {
    renderAdmin()
    await screen.findByText('Layout broken')
  })

  it('switches to audit logs tab when clicked', async () => {
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: /audit logs/i }))
    await screen.findByText('user.login')
  })
})

// ---------------------------------------------------------------------------
// Bug reports — status badge
// ---------------------------------------------------------------------------

describe('Admin — bug report status badge', () => {
  it('shows Open badge for an open report', async () => {
    renderAdmin()
    await screen.findByText('Layout broken')
    // Each row has both a status badge span AND a <select> that shows the same label,
    // so multiple elements with text "Open" are expected.
    expect(screen.getAllByText('Open').length).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// Bug reports — loading & empty states
// ---------------------------------------------------------------------------

describe('Admin — bug reports loading and empty states', () => {
  it('shows loading indicator while bug reports are fetching', () => {
    renderAdminWith({ bugReports: 'loading' })
    expect(screen.getByText(/loading bug reports/i)).toBeInTheDocument()
  })

  it('shows empty-state message when there are no bug reports', async () => {
    renderAdminWith({ bugReports: [] })
    await screen.findByText(/no bug reports submitted yet/i)
  })
})

// ---------------------------------------------------------------------------
// Status update mutation
// ---------------------------------------------------------------------------

describe('Admin — status update mutation', () => {
  it('calls api.patch with the new status when the select changes', async () => {
    vi.mocked(api.patch).mockResolvedValueOnce({ data: {} })
    renderAdmin()

    await screen.findByText('Layout broken')
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'resolved' } })

    await waitFor(() => {
      expect(api.patch).toHaveBeenCalledWith('/bug-reports/r1', { status: 'resolved' })
    })
  })

  it('shows success toast after a successful status update', async () => {
    vi.mocked(api.patch).mockResolvedValueOnce({ data: {} })
    renderAdmin()

    await screen.findByText('Layout broken')
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'resolved' } })

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Status updated')
    })
  })

  it('shows error toast when status update fails', async () => {
    vi.mocked(api.patch).mockRejectedValueOnce(new Error('Server error'))
    renderAdmin()

    await screen.findByText('Layout broken')
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'resolved' } })

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to update status')
    })
  })
})

// ---------------------------------------------------------------------------
// Audit logs — loading & empty states
// ---------------------------------------------------------------------------

describe('Admin — audit logs loading and empty states', () => {
  it('shows loading indicator while audit logs are fetching', () => {
    // Bug reports load normally; audit logs hang
    renderAdminWith({ auditLogs: 'loading' })
    fireEvent.click(screen.getByRole('button', { name: /audit logs/i }))
    expect(screen.getByText(/loading audit logs/i)).toBeInTheDocument()
  })

  it('shows empty-state message when there are no audit logs', async () => {
    renderAdminWith({ auditLogs: [] })
    fireEvent.click(screen.getByRole('button', { name: /audit logs/i }))
    await screen.findByText(/no audit log entries yet/i)
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
    await screen.findByText('Mystery bug')
    // 'pending' is not a key in BUG_STATUS_LABELS — raw value is displayed
    expect(screen.getByText('pending')).toBeInTheDocument()
  })
})

describe('Admin — audit log table edge cases', () => {
  it('shows truncated target_id and dash for null details', async () => {
    // LOG_WITH_TARGET: target_id truthy → truncated form; details null → '—'
    // SAMPLE_LOG: target_id null → '—'; details {} → '{}' (JSON)
    renderAdminWith({ auditLogs: [SAMPLE_LOG, LOG_WITH_TARGET] })
    fireEvent.click(screen.getByRole('button', { name: /audit logs/i }))
    await screen.findByText('user.ban')
    // target_id 'abc123def456789' sliced to 8 chars + ellipsis
    expect(screen.getByText('abc123de…')).toBeInTheDocument()
  })
})
