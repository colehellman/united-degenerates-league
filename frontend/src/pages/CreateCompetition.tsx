import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import { extractErrorMessage } from '../utils/errors'

interface League {
  id: string
  name: string
  display_name: string
  is_team_based: boolean
}

export default function CreateCompetition() {
  const navigate = useNavigate()

  // Format current local time as YYYY-MM-DDTHH:MM for the datetime-local min attribute.
  // datetime-local inputs operate in browser-local time, so we must use local (not UTC) values here.
  const pad = (n: number) => String(n).padStart(2, '0')
  const _now = new Date()
  const startDateMin = `${_now.getFullYear()}-${pad(_now.getMonth() + 1)}-${pad(_now.getDate())}T${pad(_now.getHours())}:${pad(_now.getMinutes())}`

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [mode, setMode] = useState('daily_picks')
  const [leagueId, setLeagueId] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [visibility, setVisibility] = useState('private')
  const [joinType, setJoinType] = useState('open')
  const [maxParticipants, setMaxParticipants] = useState('')
  const [maxPicksPerDay, setMaxPicksPerDay] = useState('')
  const [maxTeamsPerParticipant, setMaxTeamsPerParticipant] = useState('')

  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const { data: leagues, isLoading: leaguesLoading } = useQuery<League[]>({
    queryKey: ['leagues'],
    queryFn: async () => {
      const response = await api.get('/leagues')
      return response.data
    },
  })

  const selectedLeague = leagues?.find((l) => l.id === leagueId)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!leagueId) {
      setError('Please select a league')
      return
    }

    if (!startDate || !endDate) {
      setError('Start and end dates are required')
      return
    }

    if (new Date(startDate) < new Date()) {
      setError('Start date cannot be in the past')
      return
    }

    if (new Date(endDate) <= new Date(startDate)) {
      setError('End date must be after start date')
      return
    }

    setLoading(true)

    try {
      const payload: Record<string, any> = {
        name,
        description: description || null,
        mode,
        league_id: leagueId,
        start_date: startDate,
        end_date: endDate,
        visibility,
        join_type: joinType,
        max_participants: maxParticipants ? parseInt(maxParticipants) : null,
      }

      // Mode-specific fields
      if (mode === 'daily_picks' && maxPicksPerDay) {
        payload.max_picks_per_day = parseInt(maxPicksPerDay)
      }
      if (mode === 'fixed_teams' && maxTeamsPerParticipant) {
        payload.max_teams_per_participant = parseInt(maxTeamsPerParticipant)
      }

      const response = await api.post('/competitions', payload)
      navigate(`/competitions/${response.data.id}`)
    } catch (err: unknown) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  if (leaguesLoading) {
    return <div className="text-center py-8">Loading...</div>
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Create Competition</h1>

      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">
              Competition Name
            </label>
            <input
              id="name"
              type="text"
              required
              maxLength={200}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. NFL Week 15 Picks"
              className="input mt-1"
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700">
              Description <span className="text-gray-400">(optional)</span>
            </label>
            <textarea
              id="description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What's this competition about?"
              className="input mt-1"
            />
          </div>

          {/* League */}
          <div>
            <label htmlFor="league" className="block text-sm font-medium text-gray-700">
              League
            </label>
            <select
              id="league"
              required
              value={leagueId}
              onChange={(e) => setLeagueId(e.target.value)}
              className="input mt-1"
            >
              <option value="">Select a league...</option>
              {leagues?.map((league) => (
                <option key={league.id} value={league.id}>
                  {league.name} — {league.display_name}
                </option>
              ))}
            </select>
          </div>

          {/* Mode */}
          <div>
            <label htmlFor="mode" className="block text-sm font-medium text-gray-700">
              Competition Mode
            </label>
            <select
              id="mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="input mt-1"
            >
              <option value="daily_picks">Daily Picks — pick game winners each day</option>
              <option value="fixed_teams">Fixed Teams — select teams at the start, earn points from their wins</option>
            </select>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="startDate" className="block text-sm font-medium text-gray-700">
                Start Date
              </label>
              <input
                id="startDate"
                type="datetime-local"
                required
                min={startDateMin}
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="input mt-1"
              />
            </div>
            <div>
              <label htmlFor="endDate" className="block text-sm font-medium text-gray-700">
                End Date
              </label>
              <input
                id="endDate"
                type="datetime-local"
                required
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="input mt-1"
              />
            </div>
          </div>

          {/* Visibility & Join Type */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="visibility" className="block text-sm font-medium text-gray-700">
                Visibility
              </label>
              <select
                id="visibility"
                value={visibility}
                onChange={(e) => setVisibility(e.target.value)}
                className="input mt-1"
              >
                <option value="private">Private — invite only</option>
                <option value="public">Public — anyone can find it</option>
              </select>
            </div>
            <div>
              <label htmlFor="joinType" className="block text-sm font-medium text-gray-700">
                Join Policy
              </label>
              <select
                id="joinType"
                value={joinType}
                onChange={(e) => setJoinType(e.target.value)}
                className="input mt-1"
              >
                <option value="open">Open — anyone can join</option>
                <option value="requires_approval">Approval Required</option>
              </select>
            </div>
          </div>

          {/* Max Participants */}
          <div>
            <label htmlFor="maxParticipants" className="block text-sm font-medium text-gray-700">
              Max Participants <span className="text-gray-400">(leave blank for unlimited)</span>
            </label>
            <input
              id="maxParticipants"
              type="number"
              min={2}
              value={maxParticipants}
              onChange={(e) => setMaxParticipants(e.target.value)}
              placeholder="Unlimited"
              className="input mt-1"
            />
          </div>

          {/* Mode-specific settings */}
          {mode === 'daily_picks' && (
            <div>
              <label htmlFor="maxPicksPerDay" className="block text-sm font-medium text-gray-700">
                Max Picks Per Day <span className="text-gray-400">(leave blank for unlimited)</span>
              </label>
              <input
                id="maxPicksPerDay"
                type="number"
                min={1}
                value={maxPicksPerDay}
                onChange={(e) => setMaxPicksPerDay(e.target.value)}
                placeholder="Unlimited"
                className="input mt-1"
              />
            </div>
          )}

          {mode === 'fixed_teams' && selectedLeague?.is_team_based && (
            <div>
              <label htmlFor="maxTeams" className="block text-sm font-medium text-gray-700">
                Teams Per Participant <span className="text-gray-400">(leave blank for unlimited)</span>
              </label>
              <input
                id="maxTeams"
                type="number"
                min={1}
                value={maxTeamsPerParticipant}
                onChange={(e) => setMaxTeamsPerParticipant(e.target.value)}
                placeholder="Unlimited"
                className="input mt-1"
              />
            </div>
          )}

          {/* Submit */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary flex-1"
            >
              {loading ? 'Creating...' : 'Create Competition'}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="btn bg-gray-200 text-gray-700 hover:bg-gray-300 flex-1"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
