// Dashboard.test.tsx

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './Dashboard'
import api from '../services/api'

vi.mock('../services/api', () => ({
  default: { get: vi.fn() },
}))

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => { document.title = '' })
beforeEach(() => vi.clearAllMocks())

describe('Dashboard — loading state', () => {
  it('shows spinner while fetching', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}))
    renderDashboard()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

describe('Dashboard — error state', () => {
  it('shows error message instead of empty state when the API fails', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('Network error'))
    renderDashboard()
    await screen.findByText(/failed to load competitions/i)
    expect(screen.queryByText(/haven't joined/i)).not.toBeInTheDocument()
  })
})

describe('Dashboard — document title', () => {
  it('sets document.title to Dashboard | UDL', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: [] })
    renderDashboard()
    await screen.findByText(/haven't joined/i)
    expect(document.title).toBe('Dashboard | UDL')
  })
})

describe('Dashboard — empty state', () => {
  it('shows empty state when user has no competitions', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: [] })
    renderDashboard()

    await screen.findByText(/haven't joined any competitions/i)
  })

  it('renders links to create and browse competitions', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: [] })
    renderDashboard()

    await screen.findByText(/haven't joined any competitions/i)
    expect(screen.getByRole('link', { name: /create competition/i })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /browse competitions/i }).length).toBeGreaterThan(0)
  })
})

describe('Dashboard — active competitions', () => {
  it('renders active competition cards', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: [
        { id: '1', name: 'March Madness', status: 'active', mode: 'daily_picks', participant_count: 10 },
      ],
    })
    renderDashboard()

    await screen.findByText('March Madness')
    expect(screen.getByText('Active Competitions')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('10 participants')).toBeInTheDocument()
  })
})

describe('Dashboard — mode text formatting', () => {
  it('formats mode with underscores as readable words', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: [{ id: '1', name: 'NBA Picks', status: 'active', mode: 'daily_picks', participant_count: 5 }],
    })
    renderDashboard()
    await screen.findByText('NBA Picks')
    expect(screen.getByText('daily picks')).toBeInTheDocument()
    expect(screen.queryByText('daily_picks')).not.toBeInTheDocument()
  })
})

describe('Dashboard — upcoming competitions', () => {
  it('renders upcoming competition section', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: [
        { id: '2', name: 'Spring Picks', status: 'upcoming', mode: 'fixed_teams', participant_count: 3 },
      ],
    })
    renderDashboard()

    await screen.findByText('Spring Picks')
    expect(screen.getByText('Upcoming Competitions')).toBeInTheDocument()
    expect(screen.getByText('Upcoming')).toBeInTheDocument()
  })

  it('renders both active and upcoming sections simultaneously', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: [
        { id: '1', name: 'Live Comp', status: 'active', mode: 'daily_picks', participant_count: 5 },
        { id: '2', name: 'Future Comp', status: 'upcoming', mode: 'daily_picks', participant_count: 1 },
      ],
    })
    renderDashboard()

    await screen.findByText('Live Comp')
    expect(screen.getByText('Future Comp')).toBeInTheDocument()
    expect(screen.getByText('Active Competitions')).toBeInTheDocument()
    expect(screen.getByText('Upcoming Competitions')).toBeInTheDocument()
  })
})
