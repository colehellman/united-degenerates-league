import React from 'react'
import Spinner from './Spinner'

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
    return <Spinner />
  }

  if (!entries || entries.length === 0) {
    return <p className="text-gray-600">No participants yet.</p>
  }

  return (
    <>
      {/* Desktop table */}
      <div className="hidden sm:block overflow-x-auto">
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

      {/* Mobile card list */}
      <div className="sm:hidden space-y-2">
        {entries.map((entry) => (
          <div
            key={entry.user_id}
            className={`rounded-lg border p-3 ${
              entry.is_current_user
                ? 'border-primary-300 bg-primary-50'
                : 'border-gray-200'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-gray-400">#{entry.rank}</span>
                <span className="font-semibold">
                  {entry.username}
                  {entry.is_current_user && (
                    <span className="ml-1 text-primary-600 text-sm">(You)</span>
                  )}
                </span>
              </div>
              <span className="text-lg font-bold">{entry.total_points} pts</span>
            </div>
            <div className="flex gap-4 text-xs text-gray-500">
              <span>{entry.total_wins} wins</span>
              <span>{entry.accuracy_percentage.toFixed(1)}% accuracy</span>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

export default Leaderboard
