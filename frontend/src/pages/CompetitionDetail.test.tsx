// CompetitionDetail.test.tsx
//
// Focused tests for UX changes: back link on not-found, inline delete confirm,
// success toasts on picks submit, and keyboard accessibility of pick cards.

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CompetitionDetail from './CompetitionDetail'
import api from '../services/api'
import toast from 'react-hot-toast'

vi.mock('../services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}))
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const BASE_COMPETITION = {
  id: 'comp-1',
  name: 'Test League',
  description: 'Weekly picks',
  status: 'active',
  mode: 'daily_picks',
  visibility: 'public',
  join_type: 'open',
  participant_count: 5,
  max_participants: null,
  max_picks_per_day: 3,
  start_date: '2026-01-01',
  end_date: '2026-12-31',
  league: null,
  user_is_participant: true,
  user_is_admin: false,
}

const ADMIN_COMPETITION = { ...BASE_COMPETITION, user_is_admin: true }

// A game far in the future so isGameLocked returns false
const OPEN_GAME = {
  id: 'game-1',
  status: 'scheduled',
  scheduled_start_time: '2099-12-31T23:00:00Z',
  away_team: { id: 'team-away', name: 'Away Team', city: 'Springfield' },
  home_team: { id: 'team-home', name: 'Home Team', city: 'Shelbyville' },
  away_team_score: null,
  home_team_score: null,
  venue_name: null,
  spread: null,
}

const GAME_WITH_SPREAD = { ...OPEN_GAME, spread: -7.5 }
const GAME_WITH_POSITIVE_SPREAD = { ...OPEN_GAME, spread: 3 }

// ---------------------------------------------------------------------------
// Render helper
// ---------------------------------------------------------------------------

function renderDetail(competitionData: any, gamesData: any[] = [OPEN_GAME]) {
  vi.mocked(api.get).mockImplementation((url: string) => {
    if (url === '/competitions/comp-1') return Promise.resolve({ data: competitionData })
    if (url.includes('/leaderboards/')) return Promise.resolve({ data: [] })
    if (url.includes('/games')) return Promise.resolve({ data: gamesData })
    if (url.includes('/my-picks')) return Promise.resolve({ data: [] })
    if (url.includes('/my-fixed-selections')) return Promise.resolve({ data: [] })
    if (url.includes('/available-selections')) return Promise.resolve({ data: { teams: [], golfers: [] } })
    return Promise.resolve({ data: [] })
  })

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/competitions/comp-1']}>
        <Routes>
          <Route path="/competitions/:id" element={<CompetitionDetail />} />
          <Route path="/competitions" element={<div>Competitions page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => vi.clearAllMocks())

// ---------------------------------------------------------------------------
// Not-found state
// ---------------------------------------------------------------------------

describe('CompetitionDetail — not found', () => {
  it('shows a back link to /competitions when competition is not found', async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url === '/competitions/comp-1') return Promise.resolve({ data: null })
      return Promise.resolve({ data: [] })
    })

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/competitions/comp-1']}>
          <Routes>
            <Route path="/competitions/:id" element={<CompetitionDetail />} />
            <Route path="/competitions" element={<div>Competitions page</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await screen.findByText(/competition not found/i)
    expect(screen.getByRole('link', { name: /back to competitions/i })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Inline delete confirm
// ---------------------------------------------------------------------------

describe('CompetitionDetail — delete confirmation', () => {
  it('shows inline confirm UI when delete is clicked (no window.confirm)', async () => {
    const windowConfirm = vi.spyOn(window, 'confirm')
    renderDetail(ADMIN_COMPETITION)

    await screen.findByText('Test League')
    fireEvent.click(screen.getByRole('button', { name: /delete competition/i }))

    expect(screen.getByRole('button', { name: /confirm delete/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    expect(windowConfirm).not.toHaveBeenCalled()
    windowConfirm.mockRestore()
  })

  it('dismisses confirm UI when cancel is clicked', async () => {
    renderDetail(ADMIN_COMPETITION)

    await screen.findByText('Test League')
    fireEvent.click(screen.getByRole('button', { name: /delete competition/i }))
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))

    expect(screen.queryByRole('button', { name: /confirm delete/i })).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Success toast on picks submit
// ---------------------------------------------------------------------------

describe('CompetitionDetail — picks success toast', () => {
  it('shows success toast after picks are submitted', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: {} })
    renderDetail(BASE_COMPETITION)

    // Wait for the game to render
    await screen.findByText('Away Team')

    // Select the away team pick
    fireEvent.click(screen.getByText('Away Team').closest('[role="button"]')!)

    // Click submit
    fireEvent.click(screen.getByRole('button', { name: /submit 1 pick/i }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Picks saved!')
    })
  })
})

// ---------------------------------------------------------------------------
// Keyboard accessibility on pick cards
// ---------------------------------------------------------------------------

describe('CompetitionDetail — pick cards keyboard accessibility', () => {
  it('pick cards have role="button" and tabIndex=0', async () => {
    renderDetail(BASE_COMPETITION)
    await screen.findByText('Away Team')

    const awayCard = screen.getByText('Away Team').closest('[role="button"]')
    expect(awayCard).toHaveAttribute('tabindex', '0')
  })

  it('pressing Enter on a pick card selects it', async () => {
    renderDetail(BASE_COMPETITION)
    await screen.findByText('Away Team')

    const awayCard = screen.getByText('Away Team').closest('[role="button"]')!
    fireEvent.keyDown(awayCard, { key: 'Enter' })

    // After selection the submit button should show 1 pick
    await screen.findByRole('button', { name: /submit 1 pick/i })
  })

  it('pressing Space on a pick card selects it', async () => {
    renderDetail(BASE_COMPETITION)
    await screen.findByText('Away Team')

    const awayCard = screen.getByText('Away Team').closest('[role="button"]')!
    fireEvent.keyDown(awayCard, { key: ' ' })

    await screen.findByRole('button', { name: /submit 1 pick/i })
  })
})

// ---------------------------------------------------------------------------
// Spread display
// ---------------------------------------------------------------------------

describe('CompetitionDetail — spread display', () => {
  it('does not show spread when value is null', async () => {
    renderDetail(BASE_COMPETITION, [OPEN_GAME])
    await screen.findByText('Home Team')

    expect(screen.queryByText(/spread:/i)).not.toBeInTheDocument()
  })

  it('shows negative spread correctly', async () => {
    renderDetail(BASE_COMPETITION, [GAME_WITH_SPREAD])
    await screen.findByText(/spread: -7.5/i)
  })

  it('shows positive spread with a plus sign', async () => {
    renderDetail(BASE_COMPETITION, [GAME_WITH_POSITIVE_SPREAD])
    await screen.findByText(/spread: \+3/i)
  })
})
