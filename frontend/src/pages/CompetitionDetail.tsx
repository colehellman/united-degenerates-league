import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import api from '../services/api'

export default function CompetitionDetail() {
  const { id } = useParams()

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
  })

  if (compLoading) {
    return <div className="text-center py-8">Loading...</div>
  }

  if (!competition) {
    return <div className="card">Competition not found</div>
  }

  return (
    <div className="space-y-6">
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
                        className={entry.is_current_user ? 'bg-primary-50' : ''}
                      >
                        <td className="px-4 py-3 text-sm">{entry.rank}</td>
                        <td className="px-4 py-3 text-sm font-medium">
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

          {competition.mode === 'daily_picks' && (
            <div className="card">
              <h2 className="text-2xl font-bold mb-4">Daily Picks</h2>
              <p className="text-gray-600">
                Daily picks functionality will be available here. Select games and submit your predictions.
              </p>
            </div>
          )}

          {competition.mode === 'fixed_teams' && (
            <div className="card">
              <h2 className="text-2xl font-bold mb-4">Fixed Team Selection</h2>
              <p className="text-gray-600">
                Fixed team selection will be available here. Choose your teams before the competition starts.
              </p>
            </div>
          )}
        </>
      ) : (
        <div className="card text-center py-8">
          <p className="text-gray-600 mb-4">
            Join this competition to view details and start competing!
          </p>
          <button className="btn btn-primary">
            {competition.join_type === 'open' ? 'Join Now' : 'Request to Join'}
          </button>
        </div>
      )}
    </div>
  )
}
