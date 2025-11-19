United Degenerates League — Spec Addendum / Overrides (v2)

Important: This document extends and overrides the existing "United Degenerates League Production Application" spec.
If there is any conflict between the original spec and this addendum, this addendum takes precedence.

⸻

# 0. Versioning & Scope

## 0.1 v1 vs v2 Features

### v1 – MUST HAVE

**Supported leagues:**
- NFL
- NBA
- MLB
- NHL
- NCAA Men's Basketball (Division I only)
- NCAA Football (FBS only)
- PGA Golf (single tournaments only)

**Supported modes:**
- Daily Picks
- Fixed Teams (simple pre-season selection phase with exclusivity)

**Core features:**
- Live scoring & standings using sport-specific APIs
- Leaderboards per league
- Basic global admin dashboard and league admin tools

### v2 – NICE TO HAVE

**Additional leagues/competitions:**
- MLS
- EPL
- UCL / Europa League

**Extra polish:**
- Advanced analytics
- Badges, achievements, and other gamification
- More sophisticated visualizations

**Note:** The app is primarily intended for a small group of friends, not a public site. However, the spec keeps concepts like public/private for flexibility.

⸻

# 1. Competition / League Rules

## 1.1 League Lifecycle States

All leagues/competitions must follow a standardized lifecycle:

**upcoming**
- Create, configure, join, and make future picks.

**active**
- Games are happening; picks lock per game at each game's start time.

**completed**
- Schedule is done; standings are frozen.

### When a league becomes completed:

Automatically when:
- The league's end date has passed AND
- All games within its configured date range are finished

OR

- When the league creator or a global admin manually marks it as completed.

### After a league is completed:
- Picks/predictions cannot be edited.
- Leaderboard and historical views are read-only.

⸻

## 1.2 Game Outcome Rules (Ties, Cancellations, No Result)

If the official API result has no final winner for a game:
- Draw / tie
- Cancelled / abandoned
- No result available

Then:

**All picks for that game award 0 points.**
**No one wins or loses points on that game.**

This applies across all daily pick competitions.

### 1.2.1 Postponed vs Cancelled Games

**Postponed games that are rescheduled within the league's date range:**
- Picks remain valid for the new date/time
- Lock times automatically update to the new game start time
- Users are shown updated game time in UI

**Games postponed beyond the league's date range:**
- Treated as cancelled (0 points awarded)
- Clearly marked as "Postponed - No Result" in UI

### 1.2.2 Result Corrections

**If official results are corrected within 72 hours of game completion:**
- Points are recalculated automatically
- Leaderboard updates to reflect corrected scores
- No notification required (automatic update)

**After 72 hours:**
- Results are frozen unless manually adjusted by global admin
- Manual adjustments trigger audit log entry
- Affected users see point adjustment in their history

⸻

## 1.3 End-of-League Tie-Breaker

If, at the end of a league, two or more participants are tied in total points:
- The app leaves them tied in the leaderboard.
- The tie-breaker is a coin flip done in person.
- System provides tie notification, but does not automate the coin flip.
- A global admin or league admin may manually designate the final winner in the system (e.g., by setting a winnerUserId or marking "co-winners" if desired).

There are no additional automatic tie-breakers beyond total points.

⸻

## 1.4 Fixed Teams – Pre-Season Selection Phase

For Fixed Teams leagues:

### 1.4.1 Team-Based Sports (NFL, NBA, MLB, NHL, NCAA)

**Pre-season selection phase:**
- All participants choose their teams before the league's start date.
- Number of teams selectable per participant is defined by league configuration:
  - `maxTeamsPerParticipant` field (e.g., 1, 3, 5)
  - Set by league creator at league creation
- Backend enforces exclusivity:
  - Each team can only be selected once per league across all participants.
  - Example: If User A selects the Chiefs, no other user can select the Chiefs.

**When the league's start date passes:**
- Fixed Teams selections are locked permanently.
- No further changes to teams are allowed.

**UI Terminology:**
"Select up to [X] team(s) for this competition. Each team can only be chosen once across all participants."

### 1.4.2 PGA Golf Tournaments

PGA tournaments operate differently since they involve individual athletes rather than teams.

**Tournament Structure:**
- Each PGA league represents a single tournament (e.g., "The Masters 2025")
- League covers the duration of one tournament only
- No season-long PGA competitions in v1

**Golfer Selection:**
- Number of golfers selectable per participant is defined by league configuration:
  - `maxGolfersPerParticipant` field (e.g., 5, 10)
  - Set by league creator at league creation
- Backend enforces exclusivity:
  - Each golfer can only be selected once per tournament/league across all participants.
  - Example: If User A selects Tiger Woods, no other user can select Tiger Woods.

**Selection Deadline:**
- Golfer selections must be completed before the tournament's first tee time (UTC)
- After first tee time, selections are locked permanently

**Scoring:**
- Each participant's score is the sum of their selected golfers' tournament scores
- Standard golf scoring applies (lower is better)
- If a golfer withdraws or is disqualified:
  - That golfer contributes 0 to the participant's score
  - Or alternatively: contributes a penalty score (configurable, e.g., +20)

**UI Terminology:**
"Select up to [X] golfer(s) for this tournament. Each golfer can only be chosen once across all participants."

⸻

# 2. League Visibility, Joining, and Group Size

## 2.1 Visibility & Join Types

Even though the app is intended for a small friend group, define visibility and join types for clarity:

**Fields:**
- `visibility`: "public" | "private"
- `joinType`: "open" | "requiresApproval"
- `maxParticipants`: optional number (null = unlimited)

**Behavior:**

**Public + open**
- Appears in Browse Leagues.
- Any approved user can join with one click.
- If `maxParticipants` is set and reached, league shows as "Full"

**Private + requiresApproval**
- Does not appear in Browse.
- Join requests are queued and must be approved by:
  - League creator, league admin, or global admin.

**RequiresApproval (any visibility)**
- Join requests are queued and must be approved by:
  - League creator, league admin, or global admin.

For your friend group use case, most leagues will likely be private + requiresApproval, but the app should still support public + open.

### 2.1.1 League Capacity

**When maxParticipants is reached:**
- League shows as "Full" in browse view
- Join button disabled
- Message: "This league is full ([X]/[X] participants)"
- Join requests still visible to admins but flagged as "over capacity"
- Admin can increase capacity to allow additional joins

⸻

# 3. Onboarding & Empty States

## 3.1 First-Time User Dashboard

For users with no leagues created or joined:

**Show a one-time, dismissible splash screen that includes:**
- A card or buttons:
  - "Create your first league"
  - "Join a league"
- A simple explainer:
  - Short description of Daily Picks vs Fixed Teams.
  - Brief overview of supported sports

**Behavior:**
- Shown only on first visit after account creation
- Dismissible with an "X" or "Got it" button
- Never shown again after dismissal
- Users can access similar content via Help/About section

## 3.2 Empty States

Define clear empty states:

**Daily Picks:**
- When there are no pickable games (no future games within league range):
  - Show:
    ```
    No pickable games today. Check upcoming dates to make your picks.
    ```

**Dashboard / Active Leagues:**
- If user has no active leagues:
  - Show:
    ```
    You haven't joined any competitions yet – create or join one now.
    ```
  - Include prominent "Create League" and "Browse Leagues" buttons

**Leaderboard (no participants yet):**
- Show:
  ```
  No participants yet. Share this league to get started!
  ```

These help the app feel polished and self-explanatory.

⸻

# 4. Daily Picks UX: Date Navigation & Grouping

## 4.1 Date Navigation Controls

The Daily Picks UI must provide date navigation:
- Either:
  - A date picker
  - Or tabs/buttons: "Today", "Tomorrow", "This Week", etc.

Recommended: Combination of quick-access tabs + date picker for flexibility.

## 4.2 Group Games by Date

Games must be grouped into date sections with headers, such as:
- "Today"
- "Tomorrow"
- "Friday Nov 21"
- "Future Dates"

**Requirements:**
- Each date group has a clear header.
- UI must provide an easy way to jump between dates.
- Collapsible date sections recommended for mobile.

## 4.3 Make "Today vs Future" Obvious

Add:
- A visual chip or header per date:
  - e.g., Today, Tomorrow, Friday Nov 21
- A short note above the list:
  ```
  You can pick any future game up until kickoff. Daily limit still applies per calendar day.
  ```

This clarifies why users may see games beyond just the current day.

## 4.4 Multi-League Daily View

**If user is in multiple leagues covering the same sport:**

**Option 1: League Selector Dropdown (Recommended)**
- Dropdown at top of Daily Picks view
- Lists all leagues user is participating in
- Selecting a league filters the view to show only that league's pickable games
- Current league clearly indicated
- Pick status and limits shown per selected league

**Option 2: Combined View (v2)**
- Show all games from all leagues
- Each game row indicates which league(s) it applies to
- Pick status shown per league per game
- More complex UI, defer to v2

**Implementation for v1: League Selector Dropdown**

UI Elements:
```
┌─────────────────────────────────┐
│ League: [NFL 2025 ▼]            │
│                                 │
│ 3 of 5 picks made today         │
│ 2 games locked; 3 games open    │
└─────────────────────────────────┘
```

⸻

# 5. Leaderboard UX Improvements

## 5.1 Sorting & Filtering

Leaderboards must support:

**Sorting by:**
- Total points (default)
- Prediction accuracy %
- Wins (if tracked)
- Current streak (optional, v2)

**Filtering:**
- Optional in v1: Filter by "All participants" vs "Friends only" (if friend relationships exist in v2)

**UI Requirements:**
- Dropdown or toggle buttons for sort options
- Current sort clearly indicated
- Default: sort by total points, descending

## 5.2 Highlight Current User

**Always visually highlight the currently logged-in user's row in the leaderboard.**

Visual indicators (use one or more):
- Different background color (subtle, not garish)
- Bold text for username
- Small indicator icon (e.g., arrow or star)
- Slight border or outline

**Behavior:**
- If user is off-screen (e.g., ranked #47 in a long list):
  - Provide "Jump to My Rank" button
  - Or show sticky header with user's current rank

⸻

# 6. In-App Notifications Center (Removed)

**Note:** Per user feedback, email and push notifications are not desired at this stage.

However, in-app status indicators are still useful:

## 6.1 Status Indicators Only

Instead of a full notifications system, provide contextual status indicators:

**Dashboard Cards:**
- "⚠️ You have unpicked games starting soon"
- "✅ All picks submitted for today"
- "🏁 League XYZ has ended - View final standings"

**League Detail View:**
- Status banner showing pick completion status
- Deadline warnings for upcoming locks

**No persistent notification center, bell icon, or notification history required in v1.**

⸻

# 7. Mobile-First UI Requirements

## 7.1 Mobile-First Layout

Core flows must be designed mobile-first and responsive:
- Daily Picks
- Browse Leagues
- League Detail (leaderboard + picks)

## 7.2 Interaction Requirements

**Sticky "Submit Predictions" bar at the bottom:**
- Already in your spec, reaffirmed here as a requirement for mobile and desktop.
- Fixed position at bottom of viewport
- Contains:
  - Pick count summary
  - Submit button
  - Disabled state when no changes or invalid picks

**Large tap targets for:**
- Checkboxes (team selections): minimum 44x44px
- Buttons (submit, filter, join): minimum 48px height
- Dropdown controls: minimum 44px height

**Test at common breakpoints:**
- 360px (small phones - Samsung Galaxy S8, etc.)
- 375px (iPhone SE, iPhone 12/13 mini)
- 414px (iPhone Pro Max models)
- 768px (tablets - iPad)
- 1024px (small laptops)
- 1440px+ (desktop)

**Testing methodology:**
- Manual testing on real devices (minimum: iPhone, Android phone, iPad)
- Browser DevTools responsive mode for all breakpoints
- Test both portrait and landscape orientations
- Verify touch targets meet minimum size requirements
- Test with browser zoom at 150% and 200%

**Key responsive behaviors:**
- Navigation collapses to hamburger menu < 768px
- Tables convert to stacked cards < 768px
- Multi-column layouts stack to single column < 768px
- Font sizes scale appropriately (16px minimum for body text on mobile)

⸻

# 8. Visual Clarity for Lock Status

## 8.1 Per-Game Status Badges

Every game in the Daily Picks list must show a clear status badge:
- **OPEN** (green) – game is in the future; picks editable.
- **LOCKED** (gray/red) – game's UTC start time has passed; picks locked.
- **IN PROGRESS** (yellow/orange) – game has started but not yet final (optional, nice to have)
- **FINAL** (blue) – game has concluded; results recorded

**Badge styling:**
- Prominent placement (next to game time or team names)
- Color-coded backgrounds
- High contrast text
- Icon + text (e.g., 🔓 OPEN, 🔒 LOCKED)

Badges should be visually obvious and consistent across the app.

### 8.1.1 Real-Time Lock Updates

**Lock status updates automatically in UI without page refresh:**
- Use polling (every 60 seconds) or WebSocket connection
- Update lock status badges dynamically as game times approach
- Update pick submission validity in real-time

**Countdown timer for games starting within 1 hour:**
- Show live countdown next to game: "Locks in 45:23"
- Updates every second
- Turns red when < 10 minutes remaining
- Provides visual urgency

**If user attempts to submit picks for a game that just locked:**
- Show clear error message:
  ```
  Some of your picks have locked and cannot be submitted:
  • Patriots vs Bills (locked 2 minutes ago)
  
  Your other picks have been saved successfully.
  ```
- Allow resubmission of remaining valid picks
- Remove locked games from the submission
- Provide "Review Picks" button to see what was/wasn't saved

**UI behavior:**
- Disable checkboxes/selectors for locked games
- Gray out locked games in the list
- Show clear visual distinction between editable and locked

## 8.2 League-Level Summary

At the league level (Daily Picks view), show a summary:

```
3 of 5 picks made today; 2 games locked; 3 games open.
```

**Update this dynamically as time passes and picks are made.**

**Additional summary elements:**
- Progress bar showing pick completion
- Next deadline countdown (time until next game locks)
- Total points earned so far this day (if games have completed)

⸻

# 9. League Admins & Global Admin Guardrails

## 9.1 Multiple League Admins

Add support for league-level admin roles:

**Field:** `leagueAdmins: [userId]`

**Behavior:**
- League creator is automatically included as the default admin.
- League creator (and global admins) can add/remove leagueAdmins.
- League admins can:
  - Approve join requests (if requiresApproval).
  - Change league settings (non-destructive where allowed).
  - Change league status (upcoming → active, etc.), subject to overall rules.
  - View audit logs for their league.

This prevents a single person from being a bottleneck for status changes or management.

**UI for managing admins:**
- League settings page
- List of current admins
- "Add Admin" button (search for user by username/email)
- "Remove Admin" button (with confirmation)
- Cannot remove the league creator from admin role

## 9.2 Audit Log & Delete Guardrails

Implement an audit log that records admin actions, including:
- League/competition deletions
- Date range changes
- Status changes (upcoming, active, completed)
- User deletions
- Manual winner designation
- Manual score corrections
- Admin role additions/removals

**Each entry should store:**
- `who` (admin userId)
- `what` (action type)
- `when` (timestamp, UTC)
- `target` (league/user id)
- `details` (optional JSON with before/after values)

**Guardrail rule:**

**Only a global admin can delete a league/competition completely (hard delete).**
League creators and league admins may archive or deactivate, but full deletion is restricted to global admins.

### 9.2.1 Audit Log Access & Retention

**Access permissions:**
- Global admins: full access to all audit logs across all leagues
- League admins: access only to their league's audit logs
- Regular users: cannot access audit logs

**Retention policy:**
- Minimum 1 year retention
- Configurable by global admin (can extend beyond 1 year)
- Logs older than retention period can be archived/exported before deletion

**Data integrity:**
- Logs are immutable once created
- No edit or delete functions for audit log entries
- If correction needed, new entry is added with reference to original

### 9.2.2 Audit Log UI

**Features:**
- Filterable by:
  - Action type (dropdown: all, deletions, status changes, etc.)
  - Date range (date picker)
  - Admin user (dropdown of all admins)
  - League (for global admins viewing all leagues)
- Sortable by date (newest first by default)
- Exportable as CSV for external analysis
- Paginated (show 50 entries per page)

**Display format:**
```
Date/Time (UTC)  | Admin     | Action              | Target           | Details
-----------------|-----------|---------------------|------------------|------------------
2025-11-19 14:32 | admin@ex  | Status Change       | NFL 2025         | upcoming → active
2025-11-19 12:15 | creator@  | Score Correction    | Game #12345      | Team A: 24→27
```

⸻

# 10. Time Zone & Scheduling Rules (Centralized)

Create a single shared section (this one) for all time zone / scheduling logic.
All other parts of the spec that talk about dates/games should reference this section instead of restating it.

## 10.1 Storage & Logic

**All date/times are stored in UTC in the backend.**

All comparisons for:
- Game "has started" checks
- Pick locking
- League start/end checks

**Must use UTC.**

## 10.2 "Today" Definition

**For NBA-specific features:**
- "Today" for schedule display is aligned with U.S. Eastern Time if needed to match official NBA schedule expectations.

**For other sports:**
- "Today" can be defined as:
  - Midnight-to-midnight in UTC OR
  - League-specific conventions (if needed), but should be clearly derived from UTC.

## 10.3 Pick Locking

**Picks lock at each game's exact UTC start time.**

There must be no premature lock based solely on local date; the lock is per game, based on UTC.

## 10.4 UI Display

UI displays times in the user's local timezone, but:
- All business logic uses the UTC values from this section.
- Show timezone abbreviation in UI (e.g., "3:00 PM EST", "12:00 PM PST")
- Optionally: Allow users to choose display timezone in settings (v2 feature)

Other sections should phrase time requirements as:
```
Use the shared Time Zone & Scheduling Rules defined in the 'Time Zone & Scheduling Rules' section.
```

## 10.5 League Timezone Setting

**Each league has an optional "displayTimezone" field:**
- Defaults to UTC
- Commonly: "America/New_York" for US leagues
- Uses IANA timezone database format (e.g., "America/Chicago", "Europe/London")

**Used for:**
- Schedule display grouping ("Today" = league timezone midnight)
- Determining which calendar day games fall on for display purposes
- Consistent display for all users viewing the same league

**Does NOT affect:**
- Game lock times (always UTC-based)
- Backend calculations
- Pick submission deadlines

**Example:**
- League set to "America/New_York"
- Game at 2025-11-20 01:30:00 UTC
- Displays as "Nov 19 at 8:30 PM EST" for all users
- Groups under "Nov 19" in the daily picks view

⸻

# 11. NBA Data Integration (Centralized Reference)

Create a single "NBA Data Integration" subsection in the main spec and ensure:
- All NBA-related behavior (team validation, schedule fetching, caching, UTC/Eastern handling) is defined once there.
- Other sections that mention NBA should say things like:
  ```
  Use NBA data as defined in the 'NBA Data Integration' section.
  ```

This avoids duplication and keeps NBA logic centralized.

**Key topics to cover in main spec's NBA section:**
- API endpoint and authentication
- Data refresh intervals
- Team roster validation
- Schedule fetching and caching strategy
- Handling Eastern Time to UTC conversions
- Error handling for API failures
- Mapping API data to internal database schema

⸻

# 12. Data Integrity & Error Handling

## 12.1 API Failure Handling

**If sports data API is unavailable:**

**Immediate response:**
- Cache last known good data
- Serve cached data to users
- Display warning banner: "Scores may be delayed - API temporarily unavailable"
- Log incident with timestamp and error details

**Retry strategy:**
- Exponential backoff: 30s, 60s, 120s, 300s intervals
- Maximum 10 retry attempts before flagging for manual review
- Circuit breaker pattern: after 5 consecutive failures, pause retries for 10 minutes

**Admin notification:**
- Log incidents in audit log
- Flag for global admin review after 30 minutes of continuous failure
- Provide admin dashboard showing API health status

**Cache management:**
- Keep cache for up to 24 hours
- Serve stale data with prominent warning rather than showing no data
- Track cache age and display "Last updated: X minutes ago"

## 12.2 Score Correction Workflow

**If incorrect scores are detected after points are awarded:**

**Detection methods:**
- Automated: Compare API data on subsequent refreshes
- Manual: Admin notices discrepancy and flags it

**Correction process:**

1. **Within 72-hour automatic window:**
   - System detects score change via API
   - Automatically recalculates all affected picks
   - Updates leaderboard
   - Creates audit log entry
   - No user notification required (happens automatically)

2. **After 72-hour window (manual correction):**
   - Only global admin can trigger score correction
   - Admin interface shows:
     - Current recorded score
     - Proposed correction
     - Number of users/picks affected
     - Point swing preview
   - Admin must confirm correction
   - System recalculates all affected picks
   - Creates audit log entry with admin ID and justification field
   - Affected users see point adjustment in their history with explanation:
     ```
     Score corrected for Patriots vs Bills (Nov 19):
     Original: Patriots 24, Bills 27
     Corrected: Patriots 27, Bills 24
     Your points adjusted: +1
     ```

**Safeguards:**
- Corrections after league completion require extra confirmation
- Maximum 1 correction per game (prevents endless adjustments)
- Audit log retains original and corrected scores permanently

⸻

# 13. User Account Lifecycle

## 13.1 Account Deletion

**User-initiated deletion:**
- User can request account deletion from account settings
- Confirmation dialog with warning about consequences
- Grace period: 30 days before permanent deletion

**During grace period:**
- Account status set to "pending_deletion"
- User cannot log in
- Account recoverable by contacting admin or through automated reactivation link
- User removed from all leagues
- Historical picks preserved for league integrity (anonymized as "Deleted User #[ID]")

**After 30 days:**
- Permanent deletion of:
  - User profile data
  - Login credentials
  - Personal information
- Retained (anonymized):
  - Historical picks (for league standings integrity)
  - Audit log entries (admin actions)

**Admin-initiated deletion:**
- Global admin can delete user account immediately (no grace period)
- Requires justification in audit log
- Same data retention rules apply

## 13.2 Inactive Account Handling

**Accounts inactive for 365+ days:**
- Automatically flagged in admin dashboard for review
- No automatic deletion in v1
- Admin can manually review and decide to:
  - Keep as-is
  - Send reactivation email (v2 feature)
  - Delete account

**Definition of "inactive":**
- No login for 365+ consecutive days
- No picks made in any league
- No league creation or admin actions

⸻

# 14. Performance Requirements

## 14.1 Response Time Targets

**Critical user flows:**
- Page load (first contentful paint): < 2 seconds
- Daily picks submission: < 500ms
- Leaderboard refresh: < 1 second
- League creation/join: < 1 second
- Browse leagues: < 2 seconds

**Secondary flows:**
- Account settings updates: < 1 second
- Admin dashboard load: < 3 seconds
- Audit log queries: < 2 seconds

**Testing:**
- Measure on standard 4G connection (not WiFi)
- Test with realistic data volumes:
  - 100+ leagues
  - 1000+ users
  - 10,000+ picks per day

## 14.2 Caching Strategy

**Sports data (game schedules, scores):**
- Cache for 60 seconds during active game days
- Cache for 5 minutes on non-game days
- Cache invalidation on manual admin correction

**Leaderboards:**
- Cache for 30 seconds during active games
- Cache for 5 minutes when no active games
- Invalidate on pick submission or score update

**User preferences and settings:**
- Cache for 5 minutes
- Invalidate immediately on user update

**Static content:**
- Cache indefinitely with versioned URLs
- Images, CSS, JavaScript bundles

**Database query optimization:**
- Index on frequently queried fields:
  - User ID
  - League ID
  - Game start time
  - Pick submission timestamp
- Use read replicas for leaderboard queries during peak times

⸻

# 15. Glossary

Define terms consistently throughout the app:

**League**
- A professional or collegiate sports organization (e.g., NBA, NFL, NCAA, PGA)
- Represents the source of games and teams
- Examples: "NBA", "NCAA Football", "PGA Tour"

**Competition**
- A Daily Picks or Fixed Teams event that users participate in
- Has a defined start date, end date, and set of rules
- Associated with one or more leagues (e.g., "NBA 2025 Season Competition")
- Users join competitions, not leagues

**Pick / Prediction**
- Interchangeable terms for the team(s) or golfer(s) a user selects to win a game or tournament
- In Daily Picks: selecting which team will win a specific game
- In Fixed Teams: selecting which team(s) to follow for the season
- In PGA: selecting which golfer(s) to follow for a tournament
- Usage: "Make your picks" or "Submit your predictions" are equivalent

**Participant**
- A user who has joined a specific competition

**Game**
- A single matchup between two teams/competitors
- Has a specific start time, location, and eventual outcome

**Lock / Locked**
- State when a pick can no longer be edited because the game has started

**Standings**
- Current ranking of all participants in a competition based on points

**Leaderboard**
- UI display of standings (synonym)

**Global Admin**
- User with full system access across all competitions
- Can delete competitions, manage all users, access all audit logs

**League Admin**
- User with administrative access to a specific competition
- Can approve joins, change settings, manage competition lifecycle
- Note: Despite the name "League Admin", this role administers competitions, not leagues

**League Creator**
- User who originally created the competition
- Automatically a league admin
- Cannot be removed from admin role

⸻

# 16. Success Metrics

The app is working well if admins and users don't have any interruption or anything preventing them from making daily picks and a competition crowning a winner.

## 16.1 Critical Success Criteria

These are the non-negotiable requirements for the app to be considered "working":

### 16.1.1 Zero Pick Interference
**Definition:** Users must be able to submit picks without technical barriers.

**Metrics:**
- **Pick Submission Success Rate:** 99.9%+
  - Measure: (Successful pick submissions / Total pick attempts)
  - Failure causes: API errors, database timeouts, UI bugs
  
- **Lock Accuracy:** 100% within 1 second of game start
  - Measure: Picks lock at exact game start time (UTC)
  - Zero premature locks
  - Zero missed locks

- **UI Availability During Game Days:** 99.9%+
  - Measure: Uptime during hours when games are scheduled
  - Page load success rate
  - No blocking errors on pick submission page

**Acceptable Failures:**
- User error (e.g., attempting to pick after lock)
- Invalid picks (e.g., exceeding daily limit)

**Unacceptable Failures:**
- Server errors preventing valid picks
- UI crashes or freezes
- Data loss on submission
- Lock time calculation errors

### 16.1.2 Zero Competition Interruption
**Definition:** Competitions must progress from creation to winner announcement without admin intervention.

**Metrics:**
- **Automatic Competition Completion Rate:** 95%+
  - Measure: (Competitions that complete automatically / Total active competitions)
  - Competitions should transition from upcoming → active → completed without manual intervention

- **Score Accuracy:** 99.5%+
  - Measure: (Games with correct scores from API / Total games completed)
  - Manual corrections should be rare exceptions

- **Winner Declaration Success:** 100%
  - Measure: Every completed competition has a final leaderboard
  - Ties are properly identified
  - Points are correctly calculated

**Acceptable Manual Interventions:**
- Score corrections due to official API errors (< 5 per month)
- Tie-breaker winner designation
- Competition deletion (at user request)

**Unacceptable Situations:**
- Competition cannot complete due to system error
- Missing or incorrect scores preventing leaderboard calculation
- Data corruption affecting standings
- Lost picks or point calculations

### 16.1.3 Admin Zero-Friction Management
**Definition:** Admins should rarely need to intervene, and when they do, it should be effortless.

**Metrics:**
- **Required Manual Interventions:** < 5 per month across all competitions
  - Measure: Audit log entries for manual corrections or adjustments
  - Excludes user-requested actions (deletions, settings changes)

- **Admin Task Completion Time:** < 2 minutes per task
  - Measure: Time from admin login to task completion
  - Tasks: score correction, competition status change, user management

- **System Health Visibility:** Real-time
  - Admin dashboard always shows current system status
  - API health indicators
  - Failed background jobs flagged immediately

## 16.2 Secondary Metrics (Monitoring Only)

These metrics help identify trends but don't define "working" status:

**User Engagement:**
- Daily Active Users on game days
- Pick completion rate per user
- Competition abandonment rate

**Performance:**
- Average page load time
- API response time percentiles
- Database query performance

**Data Quality:**
- Cache hit rates
- API call success rates
- Background job success rates

## 16.3 Monitoring & Alerting

**Real-time alerts for:**
- Pick submission success rate drops below 99%
- Score sync fails for > 5 minutes
- API uptime drops below 99%
- Database connection failures
- Background job failures

**Daily reports for:**
- Manual intervention count
- Competition completion status
- Score correction summary
- System performance overview

**Weekly reviews:**
- Trend analysis for all metrics
- Identification of recurring issues
- User feedback themes

⸻

# 17. Reference Architecture (High-Level)

## 17.1 System Components

**Frontend:**
- React-based web application
- Responsive design (mobile-first)
- Real-time updates via polling or WebSocket

**Backend API:**
- RESTful API (or GraphQL)
- Authentication and authorization
- Business logic for picks, scoring, leagues

**Database:**
- Primary database: PostgreSQL or similar relational DB
- Stores: users, leagues, picks, games, audit logs
- Read replicas for leaderboard queries

**External Sports Data APIs:**
- NBA, NFL, MLB, NHL, NCAA, PGA data providers
- Rate limiting and caching layer
- Fallback to cached data on failures

**Background Jobs:**
- Score updates (every 60 seconds during active games)
- League status updates (check for completion)
- Cache invalidation
- Data cleanup tasks

**Admin Dashboard:**
- Separate interface or privileged section of main app
- Audit log viewer
- Manual override tools
- System health monitoring

## 17.2 Reference Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                              USERS                                   │
│                         (Web Browsers)                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ HTTPS
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                         FRONTEND LAYER                               │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  React Single-Page Application                              │    │
│  │  • Responsive UI (mobile-first)                             │    │
│  │  • Real-time polling (60s intervals)                        │    │
│  │  • State management (Redux/Context)                         │    │
│  │  • Client-side caching                                      │    │
│  └────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ REST/GraphQL API
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                         BACKEND API LAYER                            │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  API Server (Node.js/Python/etc.)                          │    │
│  │  • Authentication & Authorization                           │    │
│  │  • Business logic validation                                │    │
│  │  • Rate limiting                                            │    │
│  │  • Request/response caching                                 │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Background Job Processor                                    │    │
│  │  • Score sync (every 60s)                                   │    │
│  │  • Competition status updates                               │    │
│  │  • Cache invalidation                                       │    │
│  │  • Scheduled maintenance tasks                              │    │
│  └────────────────────────────────────────────────────────────┘    │
└──────────┬───────────────────────────────┬────────────────────┬─────┘
           │                               │                    │
           │                               │                    │
           ▼                               ▼                    ▼
┌─────────────────────┐   ┌──────────────────────┐   ┌─────────────────┐
│   DATABASE LAYER    │   │   CACHE LAYER        │   │  EXTERNAL APIs  │
│                     │   │                      │   │                 │
│ ┌─────────────────┐ │   │ ┌──────────────────┐│   │ ┌─────────────┐ │
│ │   PostgreSQL    │ │   │ │   Redis Cache    ││   │ │  NBA API    │ │
│ │   Primary DB    │ │   │ │  • Scores (60s)  ││   │ └─────────────┘ │
│ │                 │ │   │ │  • Leaderboards  ││   │                 │
│ │  • Users        │ │   │ │    (30s)         ││   │ ┌─────────────┐ │
│ │  • Competitions │ │   │ │  • User prefs    ││   │ │  NFL API    │ │
│ │  • Picks        │ │   │ │    (5m)          ││   │ └─────────────┘ │
│ │  • Games        │ │   │ └──────────────────┘│   │                 │
│ │  • Audit logs   │ │   └──────────────────────┘   │ ┌─────────────┐ │
│ └─────────────────┘ │                              │ │  MLB API    │ │
│                     │                              │ └─────────────┘ │
│ ┌─────────────────┐ │                              │                 │
│ │  Read Replicas  │ │                              │ ┌─────────────┐ │
│ │  (for heavy     │ │                              │ │  NHL API    │ │
│ │   queries)      │ │                              │ └─────────────┘ │
│ └─────────────────┘ │                              │                 │
└─────────────────────┘                              │ ┌─────────────┐ │
                                                     │ │  NCAA API   │ │
                                                     │ └─────────────┘ │
┌─────────────────────────────────────────────────┐ │                 │
│         ADMIN DASHBOARD                         │ │ ┌─────────────┐ │
│  • Audit log viewer                             │ │ │  PGA API    │ │
│  • Manual score corrections                     │ │ └─────────────┘ │
│  • Competition management                       │ └─────────────────┘
│  • System health monitoring                     │
│  • User management                              │
└─────────────────────────────────────────────────┘

DATA FLOW EXAMPLES:

[User Makes a Pick]
User → Frontend → API Server → Database → Response → Frontend

[Score Update (Background)]
External API → Background Job → Database → Cache Invalidation → 
Real-time Update → Frontend (via polling)

[Leaderboard View]
User → Frontend → API Server → Check Cache → 
  (if miss) → Database (read replica) → Cache → Response → Frontend
```

## 17.3 Data Flow Details

**User makes a pick:**
1. Frontend validates pick (not locked, within limits)
2. API receives pick, validates again
3. Database stores pick with timestamp
4. Cache invalidated for user's competition leaderboard
5. Response returned to frontend

**Score update:**
1. Background job fetches latest scores from sports API
2. Compares with cached data to detect changes
3. If changed, updates database
4. Recalculates affected picks and points
5. Invalidates leaderboard cache
6. Real-time update pushed to connected clients (if using WebSocket)

**Competition completion:**
1. Background job checks all active competitions
2. For each competition:
   - Check if end date passed
   - Check if all games completed
   - If both true, mark as "completed"
3. Freeze standings
4. Create audit log entry

⸻

# 18. API Rate Limits

## 18.1 External Sports Data APIs

**Rate limits vary by provider:**
- Document specific limits for each API (NBA, NFL, etc.)
- Typical limits: 100-1000 requests per hour

**Handling rate limits:**

**Caching:**
- Cache all API responses for minimum 60 seconds
- Serve cached data before making new API calls
- Extend cache during rate limit errors

**Request throttling:**
- Distribute requests evenly across the hour
- Priority system:
  - High: Live games in progress
  - Medium: Games starting within 24 hours
  - Low: Games starting > 24 hours away

**Rate limit exceeded:**
- Serve cached data (even if stale)
- Log rate limit error
- Notify admin if persistent
- Display warning banner: "Live scores may be delayed"

**Fallback strategies:**
- Use backup API provider if available
- Manual score entry by admin as last resort

## 18.2 Internal API Rate Limits

**To prevent abuse:**

**Per user:**
- 100 requests per minute
- 1000 requests per hour

**Exceptions:**
- Leaderboard refreshes: 10 per minute per user
- Pick submissions: 20 per minute per user

**Rate limit exceeded:**
- Return 429 Too Many Requests
- Include Retry-After header
- Block requests for 1 minute

**Whitelist:**
- Admin accounts exempt from rate limits
- Background job services exempt

⸻

# Appendix A: Summary of Changes from v1

This v2 addendum incorporates:

1. **Clarified PGA tournament structure** - single tournament only, golfer selection details
2. **Enhanced Fixed Teams flexibility** - multiple teams per participant based on league config
3. **Removed invitation system** - no invite codes or invite-based joining
4. **Added multi-league selector dropdown** - better UX for users in multiple leagues
5. **Removed notification center** - replaced with contextual status indicators only
6. **Added testing methodology** - specific breakpoints and testing procedures
7. **Enhanced real-time lock updates** - countdown timers and dynamic UI updates
8. **Added comprehensive audit log UI** - filtering, exporting, retention policies
9. **Added league timezone setting** - display timezone separate from UTC business logic
10. **Added Data Integrity section** - API failure handling and score corrections
11. **Added User Account Lifecycle section** - deletion and inactivity handling
12. **Added Performance Requirements** - specific targets and caching strategy
13. **Added Glossary** - consistent terminology
14. **Added Success Metrics** - measurable goals
15. **Added Reference Architecture** - high-level system overview
16. **Added API Rate Limits** - handling for external and internal APIs

⸻

# Appendix B: Open Questions & Future Considerations

**Questions for resolution:**

1. **PGA scoring system:**
   - Confirm: lower score is better (standard golf scoring)?
   - What penalty score for withdrawn golfers? (suggest +20 strokes)

2. **Fixed Teams point calculation:**
   - For team-based sports: sum of all selected teams' wins?
   - For PGA: sum of all selected golfers' scores?

3. **Daily Picks point values:**
   - 1 point per correct pick? Or variable based on underdog status?

4. **League privacy:**
   - Should private leagues be searchable by league name?
   - Or only joinable via direct link/code?

**Future considerations (v2+):**

- Friend/follower system for "Friends only" leaderboard filter
- Email notifications (opt-in)
- Push notifications for mobile app
- Advanced statistics (head-to-head records, hot streaks)
- Achievements and badges
- Social features (trash talk, league chat)
- Multi-season tracking and historical comparisons
- Export league history as PDF/CSV

⸻

**End of Spec Addendum v2**
