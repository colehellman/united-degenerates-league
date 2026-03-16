// InviteLanding.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import InviteLanding from './InviteLanding'
import { useAuthStore } from '../services/authStore'
import { resolveInviteToken, joinViaInvite } from '../services/api'

const mockNavigate = vi.fn()

vi.mock('../services/authStore', () => ({ useAuthStore: vi.fn() }))

vi.mock('../services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
  resolveInviteToken: vi.fn(),
  joinViaInvite: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderInvite(token = 'abc123', isAuthenticated = false) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  vi.mocked(useAuthStore).mockReturnValue({
    isAuthenticated,
    isInitializing: false,
    user: isAuthenticated ? { id: '1', email: 'a@b.com', username: 'alice', role: 'user', status: 'active' } : null,
    checkAuth: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
  } as any)
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/invite/${token}`]}>
        <Routes>
          <Route path="/invite/:token" element={<InviteLanding />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => vi.clearAllMocks())

describe('InviteLanding — unauthenticated user', () => {
  it('shows competition info and "Sign Up to Join" link pointing to register with redirect', async () => {
    vi.mocked(resolveInviteToken).mockResolvedValueOnce({
      competition_id: 'comp-1',
      competition_name: 'March Madness',
      status: 'active',
    })
    renderInvite('abc123', false)

    await screen.findByText('March Madness')
    const link = screen.getByRole('link', { name: /sign up to join/i })
    expect(link).toHaveAttribute('href', '/register?redirect=/invite/abc123')
  })
})

describe('InviteLanding — authenticated user', () => {
  it('shows "Join Competition" button for authenticated user', async () => {
    vi.mocked(resolveInviteToken).mockResolvedValueOnce({
      competition_id: 'comp-1',
      competition_name: 'March Madness',
      status: 'active',
    })
    renderInvite('abc123', true)

    await screen.findByText('March Madness')
    expect(screen.getByRole('button', { name: /join competition/i })).toBeInTheDocument()
  })

  it('calls joinViaInvite and navigates on success', async () => {
    vi.mocked(resolveInviteToken).mockResolvedValueOnce({
      competition_id: 'comp-1',
      competition_name: 'March Madness',
      status: 'active',
    })
    vi.mocked(joinViaInvite).mockResolvedValueOnce({ message: 'Joined' })
    renderInvite('abc123', true)

    await screen.findByText('March Madness')
    fireEvent.click(screen.getByRole('button', { name: /join competition/i }))

    await waitFor(() => {
      expect(joinViaInvite).toHaveBeenCalledWith('comp-1', 'abc123')
      expect(mockNavigate).toHaveBeenCalledWith('/competitions/comp-1')
    })
  })
})

describe('InviteLanding — error states', () => {
  it('shows "invite link is invalid" for 404 responses', async () => {
    vi.mocked(resolveInviteToken).mockRejectedValueOnce({
      response: { status: 404 },
    })
    renderInvite('bad-token', false)

    await screen.findByText(/invite link is invalid/i)
  })

  it('shows "competition has already ended" for 410 responses', async () => {
    vi.mocked(resolveInviteToken).mockRejectedValueOnce({
      response: { status: 410 },
    })
    renderInvite('expired-token', false)

    await screen.findByText(/competition has already ended/i)
  })
})
