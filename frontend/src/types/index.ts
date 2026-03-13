export interface Team {
  id: string
  name: string
  city: string
  abbreviation: string
  record?: string
  h2h_wins?: number
  logo_url?: string
}

export interface Game {
  id: string
  external_id: string
  scheduled_start_time: string
  status: string
  home_team: Team
  away_team: Team
  home_team_score?: number
  away_team_score?: number
  venue_name?: string
  venue_city?: string
  spread?: number
  over_under?: number
}

export type CompetitionMode = 'daily_picks' | 'fixed_teams' | 'golf_stableford'

export type CompetitionStatus = 'upcoming' | 'active' | 'completed' | 'cancelled'

export interface Competition {
  id: string
  name: string
  description?: string
  mode: CompetitionMode
  status: CompetitionStatus
  league_id: string
  start_date: string
  end_date: string
  display_timezone: string
  visibility: 'public' | 'private'
  join_type: 'open' | 'requires_approval'
  participant_count: number
  max_participants?: number
  user_is_participant: boolean
  creator_id?: string
}

export interface Participant {
  id: string
  user_id: string
  competition_id: string
  total_points: number
  total_wins: number
  total_losses: number
  accuracy_percentage: number
  current_streak: number
  joined_at: string
  last_pick_at?: string
  user?: {
    id: string
    username: string
  }
}
