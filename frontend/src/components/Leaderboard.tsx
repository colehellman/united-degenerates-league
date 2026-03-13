import React from 'react'

interface LeaderboardEntry {
  user_id: string
  username: string
  rank: number
  total_points: number
  total_wins: number
  accuracy_percentage: number
  is_current_user: boolean
}

interface LeaderboardProps {
  entries: LeaderboardEntry[]
  isLoading: boolean
}

const Leaderboard: React.FC<LeaderboardProps> = ({ entries, isLoading }) => {
  if (isLoading) {
    return <p>Loading leaderboard...</p>
  }

  if (!entries || entries.length === 0) {
    return <p className="text-gray-600">No participants yet.</p>
  }

  return (
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
          {entries.map((entry) => (
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
  )
}

export default Leaderboard
