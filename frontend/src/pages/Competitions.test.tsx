// Competitions.test.tsx

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Competitions from './Competitions'
import api from '../services/api'

vi.mock('../services/api', () => ({
  default: { get: vi.fn() },
}))

function renderCompetitions() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Competitions />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => { document.title = '' })
beforeEach(() => vi.clearAllMocks())

describe('Competitions — loading state', () => {
  it('shows spinner while fetching', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}))
    renderCompetitions()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

describe('Competitions — error state', () => {
  it('shows error message instead of empty state when the API fails', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('Network error'))
    renderCompetitions()
    await screen.findByText(/failed to load competitions/i)
    expect(screen.queryByText(/no competitions available/i)).not.toBeInTheDocument()
  })
})

describe('Competitions — document title', () => {
  it('sets document.title to Browse Competitions | UDL', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: [] })
    renderCompetitions()
    await screen.findByText(/no competitions available/i)
    expect(document.title).toBe('Browse Competitions | UDL')
  })
})

describe('Competitions — empty state', () => {
  it('shows empty state message', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: [] })
    renderCompetitions()
    await screen.findByText(/no competitions available/i)
  })
})

describe('Competitions — competition list', () => {
  const comps = [
    { id: '1', name: 'NBA Picks', status: 'active', mode: 'daily_picks', participant_count: 8, user_is_participant: true },
    { id: '2', name: 'MLB Season', status: 'upcoming', mode: 'fixed_teams', participant_count: 2, user_is_participant: false },
    { id: '3', name: 'Old Bowl', status: 'completed', mode: 'daily_picks', participant_count: 15, user_is_participant: false },
  ]

  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: comps })
  })

  it('renders competition names', async () => {
    renderCompetitions()
    await screen.findByText('NBA Picks')
    expect(screen.getByText('MLB Season')).toBeInTheDocument()
    expect(screen.getByText('Old Bowl')).toBeInTheDocument()
  })

  it('shows correct status badges', async () => {
    renderCompetitions()
    await screen.findByText('active')
    expect(screen.getByText('upcoming')).toBeInTheDocument()
    expect(screen.getByText('completed')).toBeInTheDocument()
  })

  it('shows View Details for joined competitions and Join for others', async () => {
    renderCompetitions()
    await screen.findByText('View Details')
    expect(screen.getAllByText('Join Competition').length).toBe(2)
  })

  it('shows participant counts', async () => {
    renderCompetitions()
    await screen.findByText('8 participants')
    expect(screen.getByText('2 participants')).toBeInTheDocument()
  })
})
