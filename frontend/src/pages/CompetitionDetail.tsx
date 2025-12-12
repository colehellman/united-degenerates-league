import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import api from '../services/api'

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
  const queryClient = useQueryClient()

  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0])
  const [picks, setPicks] = useState<Record<string, string>>({}) // game_id -> team_id
  const [fixedSelections, setFixedSelections] = useState<string[]>([]) // team_ids or golfer_ids
  const [error, setError] = useState('')

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

  // Fetch available games for daily picks
  const { data: games, isLoading: gamesLoading } = useQuery({
    queryKey: ['competition-games', id, selectedDate],
    queryFn: async () => {
      const response = await api.get(`/competitions/${id}/games`, {
        params: { date: selectedDate },
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
    onSuccess: (data) => {
      // Pre-populate picks state with existing picks
      const picksMap: Record<string, string> = {}
      data.forEach((pick: any) => {
        picksMap[pick.game_id] = pick.predicted_winner_team_id
      })
      setPicks(picksMap)
    },
  })

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
    onSuccess: (data) => {
      const selections = data.map((sel: any) => sel.team_id || sel.golfer_id)
      setFixedSelections(selections)
    },
  })

  // Submit daily picks mutation
  const submitPicksMutation = useMutation({
    mutationFn: async (picksData: Pick[]) => {
      const response = await api.post(`/picks/${id}/daily`, { picks: picksData })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['user-picks', id])
      queryClient.invalidateQueries(['leaderboard', id])
      setError('')
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
      queryClient.invalidateQueries(['user-fixed-selections', id])
      queryClient.invalidateQueries(['available-selections', id])
      setError('')
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
      queryClient.invalidateQueries(['competition', id])
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to join competition')
    },
  })

  const handlePickChange = (gameId: string, teamId: string) => {
    setPicks((prev) => ({
      ...prev,
      [gameId]: teamId,
    }))
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

  const getGameStatusBadge = (game: any) => {
    const now = new Date()
    const startTime = new Date(game.scheduled_start_time)
    const isLocked = startTime <= now || game.status === 'in_progress' || game.status === 'final'

    if (game.status === 'final') {
      return <span className="badge badge-final">FINAL</span>
    } else if (game.status === 'in_progress') {
      return <span className="badge badge-in-progress">LIVE</span>
    } else if (isLocked) {
      return <span className="badge" style={{ backgroundColor: '#9CA3AF', color: 'white' }}>LOCKED</span>
    } else {
      return <span className="badge badge-open">OPEN</span>
    }
  }

  const isGameLocked = (game: any) => {
    const now = new Date()
    const startTime = new Date(game.scheduled_start_time)
    return startTime <= now || game.status === 'in_progress' || game.status === 'final'
  }

  const formatGameTime = (isoString: string) => {
    const date = new Date(isoString)
    return date.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: 'short',
    })
  }

  const getPicksCount = () => {
    return Object.keys(picks).length
  }

  const getMaxPicksPerDay = () => {
    return competition?.max_picks_per_day || 'unlimited'
  }

  if (compLoading) {
    return <div className="text-center py-8">Loading...</div>
  }

  if (!competition) {
    return <div className="card">Competition not found</div>
  }

  return (
    <div className="space-y-6">
      {/* Competition Header */}
      <div className="card">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">{competition.name}</h1>
            <p className="text-gray-600">{competition.description}</p>
          </div>
          <span
            className={`badge ${
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

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
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
        </div>
      </div>

      {competition.user_is_participant ? (
        <>
          {/* Leaderboard */}
          <div className="card">
            <h2 className="text-2xl font-bold mb-4">Leaderboard</h2>
            {leaderboardLoading ? (
              <p>Loading leaderboard...</p>
            ) : leaderboard && leaderboard.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold">Rank</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold">Username</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold">Points</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold">Wins</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold">Accuracy</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {leaderboard.map((entry: any) => (
                      <tr
                        key={entry.user_id}
                        className={entry.is_current_user ? 'bg-primary-50 font-medium' : ''}
                      >
                        <td className="px-4 py-3 text-sm">{entry.rank}</td>
                        <td className="px-4 py-3 text-sm">
                          {entry.username}
                          {entry.is_current_user && (
                            <span className="ml-2 text-primary-600">(You)</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-right">{entry.total_points}</td>
                        <td className="px-4 py-3 text-sm text-right">{entry.total_wins}</td>
                        <td className="px-4 py-3 text-sm text-right">
                          {entry.accuracy_percentage.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-600">No participants yet.</p>
            )}
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
                <p>Loading games...</p>
              ) : games && games.length > 0 ? (
                <>
                  <div className="space-y-4 mb-6">
                    {games.map((game: any) => {
                      const locked = isGameLocked(game)
                      const userPick = picks[game.id]

                      return (
                        <div
                          key={game.id}
                          className={`border rounded-lg p-4 ${locked ? 'bg-gray-50' : 'bg-white'}`}
                        >
                          <div className="flex justify-between items-center mb-3">
                            <div className="text-sm text-gray-600">
                              {formatGameTime(game.scheduled_start_time)}
                            </div>
                            {getGameStatusBadge(game)}
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            {/* Away Team */}
                            <label
                              className={`border rounded-lg p-4 cursor-pointer transition ${
                                locked
                                  ? 'cursor-not-allowed opacity-60'
                                  : userPick === game.away_team.id
                                  ? 'border-primary-500 bg-primary-50'
                                  : 'border-gray-200 hover:border-primary-300'
                              }`}
                            >
                              <input
                                type="radio"
                                name={`game-${game.id}`}
                                value={game.away_team.id}
                                checked={userPick === game.away_team.id}
                                onChange={() => handlePickChange(game.id, game.away_team.id)}
                                disabled={locked}
                                className="sr-only"
                              />
                              <div className="font-semibold">{game.away_team.name}</div>
                              {game.away_team_score !== null && (
                                <div className="text-2xl font-bold mt-2">{game.away_team_score}</div>
                              )}
                            </label>

                            {/* Home Team */}
                            <label
                              className={`border rounded-lg p-4 cursor-pointer transition ${
                                locked
                                  ? 'cursor-not-allowed opacity-60'
                                  : userPick === game.home_team.id
                                  ? 'border-primary-500 bg-primary-50'
                                  : 'border-gray-200 hover:border-primary-300'
                              }`}
                            >
                              <input
                                type="radio"
                                name={`game-${game.id}`}
                                value={game.home_team.id}
                                checked={userPick === game.home_team.id}
                                onChange={() => handlePickChange(game.id, game.home_team.id)}
                                disabled={locked}
                                className="sr-only"
                              />
                              <div className="font-semibold">{game.home_team.name}</div>
                              {game.home_team_score !== null && (
                                <div className="text-2xl font-bold mt-2">{game.home_team_score}</div>
                              )}
                            </label>
                          </div>

                          {game.venue_name && (
                            <div className="text-xs text-gray-500 mt-2">
                              @ {game.venue_name}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>

                  {/* Submit Button - Sticky on mobile */}
                  <div className="sticky bottom-0 bg-white border-t pt-4 -mx-6 px-6 -mb-6 pb-6">
                    <button
                      onClick={handleSubmitPicks}
                      disabled={submitPicksMutation.isLoading || getPicksCount() === 0}
                      className="btn btn-primary w-full"
                    >
                      {submitPicksMutation.isLoading ? 'Submitting...' : `Submit ${getPicksCount()} Pick${getPicksCount() !== 1 ? 's' : ''}`}
                    </button>
                  </div>
                </>
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

                      <div className="sticky bottom-0 bg-white border-t pt-4 -mx-6 px-6 -mb-6 pb-6">
                        <div className="text-sm text-gray-600 mb-2">
                          {fixedSelections.length} of{' '}
                          {competition.max_teams_per_participant ||
                            competition.max_golfers_per_participant}{' '}
                          selected
                        </div>
                        <button
                          onClick={handleSubmitFixedSelections}
                          disabled={submitFixedSelectionsMutation.isLoading || fixedSelections.length === 0}
                          className="btn btn-primary w-full"
                        >
                          {submitFixedSelectionsMutation.isLoading
                            ? 'Submitting...'
                            : `Submit Selections`}
                        </button>
                      </div>
                    </>
                  ) : (
                    <p>Loading available selections...</p>
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
            disabled={joinMutation.isLoading}
            className="btn btn-primary"
          >
            {joinMutation.isLoading
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
