import React from 'react'
import { Game } from '../types'
import { formatGameTime, isGameLocked, getGameStatusBadge } from '../utils/format'

interface GameCardProps {
  game: Game
  userPick?: string
  onPickChange: (gameId: string, teamId: string) => void
}

const GameCard: React.FC<GameCardProps> = React.memo(function GameCard({ game, userPick, onPickChange }) {
  const locked = isGameLocked(game)

  // Helper for team card styling.
  const teamCardClass = (teamId: string) => {
    if (!locked) {
      return userPick === teamId
        ? 'border-primary-500 bg-primary-50 cursor-pointer'
        : 'border-gray-200 hover:border-primary-300 cursor-pointer'
    }
    if (userPick === teamId) {
      return 'border-primary-500 bg-primary-50 cursor-default'
    }
    return 'border-gray-100 bg-gray-50 opacity-40 cursor-default'
  }

  return (
    <div className={`border rounded-lg p-4 ${locked ? 'bg-gray-50' : 'bg-white'}`}>
      <div className="flex justify-between items-center mb-3">
        <div className="text-sm text-gray-600">
          {formatGameTime(game.scheduled_start_time)}
        </div>
        <div className="flex items-center gap-2">
          {locked && userPick && (
            <span className="text-xs font-semibold text-primary-600 uppercase tracking-wide">
              Your pick
            </span>
          )}
          {getGameStatusBadge(game)}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Away Team */}
        <div
          role="button"
          aria-pressed={userPick === game.away_team.id}
          aria-disabled={locked}
          tabIndex={locked ? undefined : 0}
          onClick={() => !locked && onPickChange(game.id, game.away_team.id)}
          onKeyDown={(e) => {
            if (!locked && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault()
              onPickChange(game.id, game.away_team.id)
            }
          }}
          className={`border rounded-lg p-3 transition select-none min-w-0 ${teamCardClass(game.away_team.id)}`}
        >
          <div className="font-semibold text-sm truncate">{game.away_team.city}</div>
          <div className="font-bold truncate">{game.away_team.name}</div>
          {game.away_team.record && (
            <div className="text-xs text-gray-500 mt-0.5">{game.away_team.record}</div>
          )}
          {game.spread !== null && game.spread !== undefined && (
            <div className="text-xs text-gray-500 mt-0.5">
              Spread: {-game.spread > 0 ? '+' : ''}{-game.spread}
            </div>
          )}
          {game.away_team_score !== null && game.away_team_score !== undefined && (
            <div className="text-2xl font-bold mt-1">{game.away_team_score}</div>
          )}
        </div>

        {/* Home Team */}
        <div
          role="button"
          aria-pressed={userPick === game.home_team.id}
          aria-disabled={locked}
          tabIndex={locked ? undefined : 0}
          onClick={() => !locked && onPickChange(game.id, game.home_team.id)}
          onKeyDown={(e) => {
            if (!locked && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault()
              onPickChange(game.id, game.home_team.id)
            }
          }}
          className={`border rounded-lg p-3 transition select-none min-w-0 ${teamCardClass(game.home_team.id)}`}
        >
          <div className="text-xs text-gray-500 font-medium">HOME</div>
          <div className="font-semibold text-sm truncate">{game.home_team.city}</div>
          <div className="font-bold truncate">{game.home_team.name}</div>
          {game.home_team.record && (
            <div className="text-xs text-gray-500 mt-0.5">{game.home_team.record}</div>
          )}
          {game.spread !== null && game.spread !== undefined && (
            <div className="text-xs text-gray-500 mt-0.5">
              Spread: {game.spread > 0 ? '+' : ''}{game.spread}
            </div>
          )}
          {game.home_team_score !== null && game.home_team_score !== undefined && (
            <div className="text-2xl font-bold mt-1">{game.home_team_score}</div>
          )}
        </div>
      </div>

      {/* Head-to-head this season */}
      {((game.away_team.h2h_wins ?? 0) > 0 || (game.home_team.h2h_wins ?? 0) > 0) && (
        <div className="text-xs text-gray-400 mt-2">
          H2H this season: {game.away_team.name} {game.away_team.h2h_wins}–{game.home_team.h2h_wins} {game.home_team.name}
        </div>
      )}

      {game.venue_name && (
        <div className="text-xs text-gray-400 mt-2">
          @ {game.venue_name}
        </div>
      )}
    </div>
  )
})

export default GameCard
