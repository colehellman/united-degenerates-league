import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import api from '../services/api'
import GameCard from '../components/GameCard'
import Leaderboard from '../components/Leaderboard'
import Spinner from '../components/Spinner'
import { isGameLocked, formatDate } from '../utils/format'

interface Pick {
  game_id: string
  predicted_winner_team_id: string
}

interface FixedTeamSelection {
  team_id?: string
  golfer_id?: string
}

export default function CompetitionDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Use local date for initialization. new Date().toISOString() returns UTC,
  // which can differ from the user's local date (e.g. 8pm ET = next day UTC).
  const _today = new Date()
  const _pad = (n: number) => String(n).padStart(2, '0')
  const [selectedDate, setSelectedDate] = useState<string>(
    `${_today.getFullYear()}-${_pad(_today.getMonth() + 1)}-${_pad(_today.getDate())}`,
  )
  const [picks, setPicks] = useState<Record<string, string>>({}) // game_id -> team_id
  const [fixedSelections, setFixedSelections] = useState<string[]>([]) // team_ids or golfer_ids
  const [error, setError] = useState('')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const { data: competition, isLoading: compLoading } = useQuery({
    queryKey: ['competition', id],
    queryFn: async () => {
      const response = await api.get(`/competitions/${id}`)
      return response.data
    },
  })

  const { data: leaderboard, isLoading: leaderboardLoading } = useQuery({
    queryKey: ['leaderboard', id],
    queryFn: async () => {
      const response = await api.get(`/leaderboards/${id}`)
      return response.data
    },
    enabled: !!competition?.user_is_participant,
    refetchInterval: 30000, // Refetch every 30s for live updates
  })

  // Fetch available games for daily picks.
  // Pass utc_offset_minutes so the backend converts the local date window to
  // the correct UTC range. JS Date.getTimezoneOffset() returns minutes west of
  // UTC (e.g. EST = 300), matching the backend parameter convention.
  const utcOffset = new Date().getTimezoneOffset()
  const { data: games, isLoading: gamesLoading } = useQuery({
    queryKey: ['competition-games', id, selectedDate, utcOffset],
    queryFn: async () => {
      const response = await api.get(`/competitions/${id}/games`, {
        params: { date: selectedDate, utc_offset_minutes: utcOffset },
      })
      return response.data
    },
    enabled: !!competition?.user_is_participant && competition?.mode === 'daily_picks',
    refetchInterval: 60000, // Refetch every 60s for lock status updates
  })

  // Fetch user's current picks
  const { data: userPicks } = useQuery({
    queryKey: ['user-picks', id, selectedDate],
    queryFn: async () => {
      const response = await api.get(`/picks/${id}/my-picks`, {
        params: { date: selectedDate },
      })
      return response.data
    },
    enabled: !!competition?.user_is_participant && competition?.mode === 'daily_picks',
  })

  // Pre-populate picks state when data arrives
  useEffect(() => {
    if (userPicks) {
      const picksMap: Record<string, string> = {}
      userPicks.forEach((pick: any) => {
        picksMap[pick.game_id] = pick.predicted_winner_team_id
      })
      setPicks(picksMap)
    }
  }, [userPicks])

  // Fetch available teams/golfers for fixed teams mode
  const { data: availableSelections } = useQuery({
    queryKey: ['available-selections', id],
    queryFn: async () => {
      const response = await api.get(`/competitions/${id}/available-selections`)
      return response.data
    },
    enabled: !!competition?.user_is_participant && competition?.mode === 'fixed_teams',
  })

  // Fetch user's current fixed team selections
  const { data: userFixedSelections } = useQuery({
    queryKey: ['user-fixed-selections', id],
    queryFn: async () => {
      const response = await api.get(`/picks/${id}/my-fixed-selections`)
      return response.data
    },
    enabled: !!competition?.user_is_participant && competition?.mode === 'fixed_teams',
  })

  // Pre-populate fixed selections state when data arrives
  useEffect(() => {
    if (userFixedSelections) {
      const selections = userFixedSelections.map((sel: any) => sel.team_id || sel.golfer_id)
      setFixedSelections(selections)
    }
  }, [userFixedSelections])

  // Submit daily picks mutation
  const submitPicksMutation = useMutation({
    mutationFn: async (picksData: Pick[]) => {
      // Pass the selected date so the backend can scope its replace semantics
      // to the correct day window (delete de-selected picks, fix limit check).
      const response = await api.post(
        `/picks/${id}/daily`,
        { picks: picksData },
        { params: { date: selectedDate } },
      )
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-picks', id] })
      queryClient.invalidateQueries({ queryKey: ['leaderboard', id] })
      setError('')
      toast.success('Picks saved!')
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to submit picks')
    },
  })

  // Submit fixed team selections mutation
  const submitFixedSelectionsMutation = useMutation({
    mutationFn: async (selections: FixedTeamSelection[]) => {
      const response = await api.post(`/picks/${id}/fixed-teams`, { selections })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-fixed-selections', id] })
      queryClient.invalidateQueries({ queryKey: ['available-selections', id] })
      setError('')
      toast.success('Selections saved!')
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to submit selections')
    },
  })

  // Join competition mutation
  const joinMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/competitions/${id}/join`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competition', id] })
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to join competition')
    },
  })

  // Admin: delete competition
  const deleteCompetitionMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/competitions/${id}`)
    },
    onSuccess: () => {
      toast.success('Competition deleted')
      navigate('/competitions')
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to delete competition')
    },
  })

  // Admin: force a game sync for this competition (runs synchronously, returns counts)
  const forceSyncMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/competitions/${id}/sync-games`)
      return response.data as { created: number; updated: number; message?: string }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['competition-games', id] })
      if (data.created > 0) {
        toast.success(`Synced ${data.created} new game${data.created !== 1 ? 's' : ''} from ESPN`)
      } else if (data.updated > 0) {
        toast.success(`Updated ${data.updated} game${data.updated !== 1 ? 's' : ''}`)
      } else {
        toast(data.message || 'No new games found from ESPN today', { icon: 'ℹ️' })
      }
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Game sync failed')
    },
  })

  // Guards against firing the auto-sync more than once per page load.
  // useMutation's mutate is stable, but re-renders would otherwise re-trigger.
  const hasAutoSynced = useRef(false)

  // Auto-sync games once on page load for admins when the games list is empty.
  // This covers the case where the backend sync on creation failed (ESPN outage,
  // circuit breaker open, etc.) or the admin navigates to an existing competition
  // with no games yet. The hasAutoSynced ref prevents re-triggering on re-renders.
  useEffect(() => {
    if (
      hasAutoSynced.current ||
      !competition?.user_is_admin ||
      gamesLoading ||
      !games ||
      games.length > 0 ||
      forceSyncMutation.isPending
    ) {
      return
    }
    hasAutoSynced.current = true
    forceSyncMutation.mutate()
  // forceSyncMutation covers .isPending and .mutate — no need to list properties separately.
  }, [competition?.user_is_admin, gamesLoading, games, forceSyncMutation])

  // True once the user has at least one persisted pick for the selected date.
  // Used to enable post-submission editing rules.
  const hasSubmittedPicks = !!(userPicks && userPicks.length > 0)

  const handlePickChange = (gameId: string, teamId: string) => {
    setPicks((prev) => {
      // Toggle off: clicking the already-selected team deselects it
      if (prev[gameId] === teamId) {
        // After submission, prevent de-selecting the only remaining unstarted game.
        // If there are no other unstarted games the user could swap to, un-picking
        // would leave them with no valid replacement and is likely a mis-click.
        // They can still switch the winner by clicking the other team.
        if (hasSubmittedPicks) {
          const otherUnstarted = (games || []).filter(
            (g: any) => g.id !== gameId && !isGameLocked(g),
          )
          if (otherUnstarted.length === 0) {
            return prev // block toggle-off; winner switch still works
          }
        }

        const next = { ...prev }
        delete next[gameId]
        setError('')
        return next
      }

      // Switching the team on an already-picked game doesn't add to the count
      const isNewGame = !prev[gameId]
      const maxPicks = competition?.max_picks_per_day
      if (isNewGame && maxPicks && Object.keys(prev).length >= maxPicks) {
        setError(
          `Competition rules only allow ${maxPicks} pick${maxPicks !== 1 ? 's' : ''} per day`,
        )
        return prev // no state change
      }

      setError('')
      return { ...prev, [gameId]: teamId }
    })
  }

  const handleFixedSelectionToggle = (selectionId: string) => {
    setFixedSelections((prev) => {
      if (prev.includes(selectionId)) {
        return prev.filter((id) => id !== selectionId)
      } else {
        // Check max limit
        const maxLimit = competition?.max_teams_per_participant || competition?.max_golfers_per_participant
        if (maxLimit && prev.length >= maxLimit) {
          setError(`You can only select up to ${maxLimit} ${competition?.league?.sport === 'PGA' ? 'golfers' : 'teams'}`)
          return prev
        }
        return [...prev, selectionId]
      }
    })
  }

  const handleSubmitPicks = () => {
    setError('')
    const picksArray: Pick[] = Object.entries(picks).map(([gameId, teamId]) => ({
      game_id: gameId,
      predicted_winner_team_id: teamId,
    }))

    if (picksArray.length === 0) {
      setError('Please select at least one pick')
      return
    }

    submitPicksMutation.mutate(picksArray)
  }

  const handleSubmitFixedSelections = () => {
    setError('')

    if (fixedSelections.length === 0) {
      setError('Please select at least one team or golfer')
      return
    }

    const selections: FixedTeamSelection[] = fixedSelections.map((id) => {
      // Determine if it's a team or golfer based on available data
      const isGolfer = availableSelections?.golfers?.some((g: any) => g.id === id)
      return isGolfer ? { golfer_id: id } : { team_id: id }
    })

    submitFixedSelectionsMutation.mutate(selections)
  }

  const getPicksCount = () => {
    return Object.keys(picks).length
  }

  const getMaxPicksPerDay = () => {
    return competition?.max_picks_per_day || 'unlimited'
  }

  // Set document title once competition data arrives
  useEffect(() => {
    if (competition?.name) {
      document.title = `${competition.name} | UDL`
      return () => { document.title = 'United Degenerates League' }
    }
  }, [competition?.name])

  if (compLoading) {
    return <Spinner />
  }

  if (!competition) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-700 font-medium mb-4">Competition not found</p>
        <Link to="/competitions" className="btn btn-secondary text-sm">
          ← Back to competitions
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Competition Header */}
      <div className="card">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 mb-4">
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-bold mb-2 break-words">{competition.name}</h1>
            {competition.description && (
              <p className="text-gray-600">{competition.description}</p>
            )}
          </div>
          <span
            className={`badge shrink-0 self-start capitalize ${
              competition.status === 'active'
                ? 'badge-in-progress'
                : competition.status === 'upcoming'
                ? 'badge-open'
                : 'badge-final'
            }`}
          >
            {competition.status}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 sm:gap-4 text-sm">
          <div>
            <p className="text-gray-600">Mode</p>
            <p className="font-semibold capitalize">{competition.mode.replace('_', ' ')}</p>
          </div>
          <div>
            <p className="text-gray-600">Participants</p>
            <p className="font-semibold">
              {competition.participant_count}
              {competition.max_participants && ` / ${competition.max_participants}`}
            </p>
          </div>
          <div>
            <p className="text-gray-600">Visibility</p>
            <p className="font-semibold capitalize">{competition.visibility}</p>
          </div>
          <div>
            <p className="text-gray-600">Join Type</p>
            <p className="font-semibold capitalize">{competition.join_type.replace('_', ' ')}</p>
          </div>
          <div>
            <p className="text-gray-600">Start Date</p>
            <p className="font-semibold">{formatDate(competition.start_date)}</p>
          </div>
          <div>
            <p className="text-gray-600">End Date</p>
            <p className="font-semibold">{formatDate(competition.end_date)}</p>
          </div>
          {competition.league && (
            <div>
              <p className="text-gray-600">League</p>
              <p className="font-semibold">{competition.league.display_name || competition.league.name}</p>
            </div>
          )}
          {competition.max_picks_per_day && (
            <div>
              <p className="text-gray-600">Max Picks/Day</p>
              <p className="font-semibold">{competition.max_picks_per_day}</p>
            </div>
          )}
        </div>
      </div>

      {/* Admin Controls — only visible to competition/global admins */}
      {competition.user_is_admin && (
        <div className="card border-l-4 border-yellow-400 bg-yellow-50">
          <h2 className="text-lg font-semibold text-yellow-800 mb-4">⚙️ Admin Controls</h2>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => {
                forceSyncMutation.mutate()
              }}
              disabled={forceSyncMutation.isPending}
              className="btn btn-secondary text-sm"
            >
              {forceSyncMutation.isPending ? 'Syncing…' : '🔄 Force Game Sync'}
            </button>
            {showDeleteConfirm ? (
              <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">Delete "{competition.name}"? This cannot be undone.</p>
                <button
                  onClick={() => { deleteCompetitionMutation.mutate(); setShowDeleteConfirm(false) }}
                  disabled={deleteCompetitionMutation.isPending}
                  className="btn text-sm bg-red-600 text-white hover:bg-red-700 whitespace-nowrap"
                >
                  Confirm Delete
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="btn btn-secondary text-sm"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={deleteCompetitionMutation.isPending}
                className="btn text-sm bg-red-600 text-white hover:bg-red-700"
              >
                🗑️ Delete Competition
              </button>
            )}
          </div>
        </div>
      )}

      {competition.user_is_participant ? (
        <>
          {/* Leaderboard */}
          <div className="card">
            <h2 className="text-2xl font-bold mb-4">Leaderboard</h2>
            <Leaderboard entries={leaderboard} isLoading={leaderboardLoading} />
          </div>

          {/* Daily Picks Mode */}
          {competition.mode === 'daily_picks' && (
            <div className="card">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">Daily Picks</h2>
                <div className="text-sm text-gray-600">
                  {getPicksCount()} of {getMaxPicksPerDay()} picks selected
                </div>
              </div>

              {/* Date Selector */}
              <div className="mb-6">
                <label htmlFor="date-select" className="block text-sm font-medium text-gray-700 mb-2">
                  Select Date
                </label>
                <input
                  id="date-select"
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="input"
                />
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
                  {error}
                </div>
              )}

              {gamesLoading ? (
                <Spinner />
              ) : games && games.length > 0 ? (
                (() => {
                  // When every game on this date has started, show only the
                  // games the user picked so they can track their results.
                  // Games with no pick made are irrelevant at that point.
                  const allLocked = games.every((g: any) => isGameLocked(g))
                  const hasPicks = Object.keys(picks).length > 0
                  const displayGames: any[] =
                    allLocked && hasPicks ? games.filter((g: any) => picks[g.id]) : games

                  return (
                    <>
                      {allLocked && hasPicks && (
                        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg mb-4 text-sm">
                          All games have started — showing your {displayGames.length} pick{displayGames.length !== 1 ? 's' : ''} for today.
                        </div>
                      )}

                      <div className="space-y-4 mb-6">
                        {displayGames.map((game: any) => (
                          <GameCard
                            key={game.id}
                            game={game}
                            userPick={picks[game.id]}
                            onPickChange={handlePickChange}
                          />
                        ))}
                      </div>

                      {/* Submit / Update button — shown while any game is still open */}
                      {!allLocked && (
                        <div className="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t pt-4 pb-4 mt-4">
                          {hasSubmittedPicks && (
                            <p className="text-xs text-gray-500 text-center mb-2">
                              Picks are editable until each game starts
                            </p>
                          )}
                          <button
                            onClick={handleSubmitPicks}
                            disabled={submitPicksMutation.isPending || getPicksCount() === 0}
                            className="btn btn-primary w-full"
                          >
                            {submitPicksMutation.isPending
                              ? 'Submitting...'
                              : hasSubmittedPicks
                              ? `Update ${getPicksCount()} Pick${getPicksCount() !== 1 ? 's' : ''}`
                              : `Submit ${getPicksCount()} Pick${getPicksCount() !== 1 ? 's' : ''}`}
                          </button>
                        </div>
                      )}
                    </>
                  )
                })()
              ) : (
                <p className="text-gray-600">
                  No pickable games for this date. Check upcoming dates to make your picks.
                </p>
              )}
            </div>
          )}

          {/* Fixed Teams Mode */}
          {competition.mode === 'fixed_teams' && (
            <div className="card">
              <h2 className="text-2xl font-bold mb-4">
                {competition.league?.sport === 'PGA' ? 'Golfer Selection' : 'Fixed Team Selection'}
              </h2>

              {competition.status === 'active' || competition.status === 'completed' ? (
                <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg mb-4">
                  Selections are locked. Competition has started.
                </div>
              ) : (
                <>
                  <p className="text-gray-600 mb-6">
                    Select up to{' '}
                    {competition.max_teams_per_participant || competition.max_golfers_per_participant}{' '}
                    {competition.league?.sport === 'PGA' ? 'golfer(s)' : 'team(s)'} for this
                    competition. Each selection can only be chosen once across all participants.
                  </p>

                  {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
                      {error}
                    </div>
                  )}

                  {availableSelections ? (
                    <>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                        {(availableSelections.teams || availableSelections.golfers || []).map(
                          (selection: any) => {
                            const isSelected = fixedSelections.includes(selection.id)
                            const isAvailable = selection.is_available !== false

                            return (
                              <label
                                key={selection.id}
                                className={`border rounded-lg p-4 cursor-pointer transition ${
                                  !isAvailable
                                    ? 'opacity-50 cursor-not-allowed bg-gray-50'
                                    : isSelected
                                    ? 'border-primary-500 bg-primary-50'
                                    : 'border-gray-200 hover:border-primary-300'
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => handleFixedSelectionToggle(selection.id)}
                                  disabled={!isAvailable && !isSelected}
                                  className="sr-only"
                                />
                                <div className="flex items-center justify-between">
                                  <div>
                                    <div className="font-semibold">{selection.name}</div>
                                    {selection.city && (
                                      <div className="text-sm text-gray-600">{selection.city}</div>
                                    )}
                                    {selection.country && (
                                      <div className="text-sm text-gray-600">{selection.country}</div>
                                    )}
                                  </div>
                                  {isSelected && (
                                    <svg
                                      className="w-6 h-6 text-primary-600"
                                      fill="none"
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M5 13l4 4L19 7"
                                      />
                                    </svg>
                                  )}
                                </div>
                                {!isAvailable && !isSelected && (
                                  <div className="text-xs text-red-600 mt-2">
                                    Already selected by another participant
                                  </div>
                                )}
                              </label>
                            )
                          }
                        )}
                      </div>

                      <div className="sticky bottom-0 bg-white/95 backdrop-blur-sm border-t pt-4 pb-4 mt-4">
                        <div className="text-sm text-gray-600 mb-2">
                          {fixedSelections.length} of{' '}
                          {competition.max_teams_per_participant ||
                            competition.max_golfers_per_participant}{' '}
                          selected
                        </div>
                        <button
                          onClick={handleSubmitFixedSelections}
                          disabled={submitFixedSelectionsMutation.isPending || fixedSelections.length === 0}
                          className="btn btn-primary w-full"
                        >
                          {submitFixedSelectionsMutation.isPending
                            ? 'Submitting...'
                            : 'Submit Selections'}
                        </button>
                      </div>
                    </>
                  ) : (
                    <Spinner />
                  )}
                </>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="card text-center py-8">
          <p className="text-gray-600 mb-4">
            Join this competition to view details and start competing!
          </p>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
              {error}
            </div>
          )}
          <button
            onClick={() => joinMutation.mutate()}
            disabled={joinMutation.isPending}
            className="btn btn-primary"
          >
            {joinMutation.isPending
              ? 'Joining...'
              : competition.join_type === 'open'
              ? 'Join Now'
              : 'Request to Join'}
          </button>
        </div>
      )}
    </div>
  )
}
