# Database Entity-Relationship Diagram

All tables use **UUID primary keys** and **UTC timestamps** (`created_at`, `updated_at`).

```
┌──────────────────────┐          ┌──────────────────────┐
│       leagues        │          │        teams         │
├──────────────────────┤          ├──────────────────────┤
│ id           (UUID)  │◄─────┐   │ id           (UUID)  │
│ name         (Enum)  │      │   │ league_id    (FK)────┼──► leagues
│ display_name (Str)   │      │   │ external_id  (Str)   │
│ is_team_based(Bool)  │      │   │ name         (Str)   │
└──────────────────────┘      │   │ abbreviation (Str)   │
                              │   │ city         (Str)   │
┌──────────────────────┐      │   │ wins/losses/ties     │
│       golfers        │      │   │ is_active    (Bool)  │
├──────────────────────┤      │   └──────────────────────┘
│ id           (UUID)  │      │            ▲
│ league_id    (FK)────┼──────┘            │
│ first_name   (Str)   │                   │
│ last_name    (Str)   │                   │
│ is_active    (Bool)  │                   │
└──────────────────────┘                   │
                                           │
┌──────────────────────┐                   │
│       users          │                   │
├──────────────────────┤                   │
│ id           (UUID)  │◄──────────┐       │
│ email        (Str)   │           │       │
│ username     (Str)   │           │       │
│ hashed_pw    (Str)   │           │       │
│ role         (Enum)  │           │       │
│ status       (Enum)  │           │       │
│ last_login_at(DT)    │           │       │
│ failed_login (Int)   │           │       │
│ locked_until (DT)    │           │       │
└──────┬───────────────┘           │       │
       │                           │       │
       │  creates                  │       │
       ▼                           │       │
┌──────────────────────────┐       │       │
│     competitions         │       │       │
├──────────────────────────┤       │       │
│ id             (UUID)    │◄──┐   │       │
│ name           (Str)     │   │   │       │
│ mode           (Enum)    │   │   │       │
│ status         (Enum)    │   │   │       │
│ league_id      (FK)──────┼───┼───┼───────┘
│ creator_id     (FK)──────┼───┼───┘
│ start_date     (DT)      │   │
│ end_date       (DT)      │   │
│ visibility     (Enum)    │   │
│ join_type      (Enum)    │   │
│ max_participants (Int)   │   │
│ max_picks_per_day (Int)  │   │
│ winner_user_id (FK)──────┼───┘
└──────┬───────────────────┘
       │
       │  has many
       ▼
┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────────┐
│   participants       │    │       games          │    │     invite_links         │
├──────────────────────┤    ├──────────────────────┤    ├──────────────────────────┤
│ id           (UUID)  │    │ id           (UUID)  │    │ id              (UUID)   │
│ user_id      (FK)────┼─►  │ competition_id(FK)───┼─►  │ competition_id  (FK)─────┼─►
│ competition_id(FK)───┼─►  │ home_team_id (FK)────┼─►  │ created_by_id   (FK)─────┼─►
│ total_points (Int)   │    │ away_team_id (FK)────┼─►  │ token           (Str)    │
│ total_wins   (Int)   │    │ status       (Enum)  │    │ is_admin_invite (Bool)   │
│ total_losses (Int)   │    │ home_team_score(Int) │    │ use_count       (Int)    │
│ accuracy_pct (Float) │    │ away_team_score(Int) │    └──────────────────────────┘
│ current_streak(Int)  │    │ winner_team_id(FK)───┼─►
│ joined_at    (DT)    │    │ scheduled_start(DT)  │
└──────────────────────┘    │ spread       (Float) │
                            │ scoring_done (Bool)  │
                            └──────────────────────┘
                                     │
                                     │  has many
                                     ▼
                            ┌──────────────────────┐
                            │       picks          │
                            ├──────────────────────┤
                            │ id           (UUID)  │
                            │ user_id      (FK)────┼─► users
                            │ competition_id(FK)───┼─► competitions
                            │ game_id      (FK)────┼─► games
                            │ predicted_winner(FK)─┼─► teams
                            │ is_locked    (Bool)  │
                            │ is_correct   (Bool)  │
                            │ points_earned(Int)   │
                            └──────────────────────┘

┌──────────────────────────┐    ┌──────────────────────┐
│    fixed_team_selections │    │    join_requests      │
├──────────────────────────┤    ├──────────────────────┤
│ id              (UUID)   │    │ id           (UUID)  │
│ user_id         (FK)─────┼─►  │ user_id      (FK)────┼─► users
│ competition_id  (FK)─────┼─►  │ competition_id(FK)───┼─► competitions
│ team_id         (FK)─────┼─►  │ status       (Enum)  │
│ golfer_id       (FK)─────┼─►  │ reviewed_by  (FK)────┼─► users
│ is_locked       (Bool)   │    │ rejection_reason(Str)│
│ total_points    (Int)    │    └──────────────────────┘
└──────────────────────────┘

┌──────────────────────┐    ┌──────────────────────┐
│    bug_reports       │    │    audit_logs        │
├──────────────────────┤    ├──────────────────────┤
│ id           (UUID)  │    │ id           (UUID)  │
│ user_id      (FK)────┼─►  │ admin_user_id(FK)────┼─► users
│ title        (Str)   │    │ action       (Enum)  │
│ description  (Str)   │    │ target_type  (Str)   │
│ status       (Enum)  │    │ target_id    (UUID)  │
│ category     (Enum)  │    │ details      (JSON)  │
│ page_url     (Str)   │    └──────────────────────┘
└──────────────────────┘
```

## Relationships Summary

| Parent | Child | Relationship | On Delete |
|--------|-------|-------------|-----------|
| users | competitions | creator_id | — |
| users | participants | user_id | cascade |
| users | picks | user_id | cascade |
| users | fixed_team_selections | user_id | cascade |
| users | bug_reports | user_id | cascade |
| users | audit_logs | admin_user_id | — |
| users | invite_links | created_by_user_id | — |
| users | join_requests | user_id | cascade |
| leagues | teams | league_id | — |
| leagues | golfers | league_id | — |
| leagues | competitions | league_id | — |
| competitions | participants | competition_id | cascade |
| competitions | games | competition_id | cascade |
| competitions | picks | competition_id | cascade |
| competitions | invite_links | competition_id | cascade |
| competitions | join_requests | competition_id | cascade |
| competitions | fixed_team_selections | competition_id | cascade |
| games | picks | game_id | — |
| teams | games | home/away_team_id | — |
| teams | picks | predicted_winner_team_id | — |
| teams | fixed_team_selections | team_id | — |

## Enums

| Enum | Values |
|------|--------|
| UserRole | user, league_admin, global_admin |
| AccountStatus | active, suspended, banned, pending_deletion, deleted |
| CompetitionMode | daily_picks, fixed_teams |
| CompetitionStatus | upcoming, active, completed |
| Visibility | public, private |
| JoinType | open, requires_approval |
| GameStatus | scheduled, in_progress, final, postponed, cancelled, no_result |
| BugReportStatus | open, in_review, resolved, closed |
| BugCategory | ui, performance, data, auth, other |
| JoinRequestStatus | pending, approved, rejected |
