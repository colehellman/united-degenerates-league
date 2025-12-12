# 🏗️ United Degenerates League - Architecture Documentation

**Version:** 2.0.0
**Last Updated:** 2025-01-11
**Status:** Development (60-70% Complete - Updated from initial 40-50% estimate)

---

## 📊 Executive Summary

**United Degenerates League (UDL)** is a sports prediction platform built with FastAPI + React, designed for friends to compete in daily picks and fixed team challenges across multiple sports leagues (NFL, NBA, MLB, NHL, NCAA, PGA).

**Architecture Pattern:** Clean Architecture / Layered Monolith
**Paradigm:** Async-first backend with reactive frontend
**Deployment:** Docker + Railway.app

### Key Metrics (Updated)
- **Backend:** 34 Python files (~3,000 LOC)
- **Frontend:** 10 TypeScript/TSX files (~2,000 LOC)
- **Database Models:** 8 core entities with proper relationships
- **API Endpoints:** 25+ RESTful routes, all complete
- **External APIs:** 5 sports data providers with failover (orchestration complete, clients pending)

### Current Status (Revised Assessment)
- ✅ **Complete (70%):** Core models, API structure, auth system, multi-API failover, frontend UI (login, register, dashboard, browse)
- 🚧 **In Progress (20%):** Background jobs, API client implementations, pick submission UI
- ❌ **Pending (10%):** Database migrations, testing infrastructure, production hardening

**Key Discovery:** Frontend is significantly more complete than initially assessed. Login and Register pages are fully implemented with proper validation, error handling, and UI polish.

---

## 📖 Table of Contents

1. [Project Structure Deep Dive](#project-structure-deep-dive)
2. [How the App Actually Works](#how-the-app-actually-works)
3. [Module-by-Module Breakdown](#module-by-module-breakdown)
4. [Data Flow Narratives](#data-flow-narratives)
5. [Important Files Map](#important-files-map)
6. [Architecture Diagrams](#architecture-diagrams)
7. [Known Issues and Technical Debt](#known-issues-and-technical-debt)
8. [Potential Improvements](#potential-improvements)
9. [Development Roadmap](#development-roadmap)

---

## 🏗️ Project Structure Deep Dive

### High-Level Directory Structure

```
udl/
├── backend/                    # Python FastAPI application
│   ├── alembic/               # Database migrations (empty - needs generation)
│   │   ├── versions/          # Migration scripts (TODO)
│   │   └── env.py             # Alembic configuration
│   ├── app/                   # Main application code
│   │   ├── api/              # HTTP endpoint handlers (7 modules)
│   │   ├── core/             # Configuration, security, dependencies
│   │   ├── db/               # Database session management
│   │   ├── models/           # SQLAlchemy ORM models (8 entities)
│   │   ├── schemas/          # Pydantic validation schemas (5 modules)
│   │   ├── services/         # Business logic and integrations
│   │   │   ├── sports_api/  # Multi-provider API abstraction
│   │   │   ├── circuit_breaker.py
│   │   │   └── background_jobs.py
│   │   └── main.py           # FastAPI app factory
│   ├── .env                   # Environment variables (gitignored)
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Container definition
│   └── alembic.ini           # Migration configuration
│
├── frontend/                  # React TypeScript application
│   ├── src/
│   │   ├── pages/            # Route components (5 pages)
│   │   ├── components/       # Reusable UI components (1 layout)
│   │   ├── services/         # API client + state management
│   │   ├── App.tsx           # Router configuration
│   │   └── main.tsx          # React entry point
│   ├── public/               # Static assets
│   ├── package.json          # Node dependencies
│   ├── vite.config.ts        # Build configuration
│   ├── tailwind.config.js    # Styling configuration
│   └── tsconfig.json         # TypeScript configuration
│
├── docker-compose.yml         # Multi-container orchestration
├── Dockerfile                # Root Dockerfile for Railway
├── railway.toml              # Railway deployment config
├── ARCHITECTURE.md           # This file
├── CODE_MAP.md              # Complete file catalog
└── README.md                # Getting started guide
```

---

## 🎬 How the App Actually Works

### The Big Picture

United Degenerates League is a **social sports prediction game** where users compete against friends by:
1. **Creating competitions** for a specific sport/league and date range
2. **Inviting friends** to join (public or private with approval)
3. **Making predictions** using one of two game modes:
   - **Daily Picks:** Pick winners for each game, earn points for correct predictions
   - **Fixed Teams:** Select teams/golfers pre-season, accumulate points based on their performance
4. **Tracking standings** on real-time leaderboards
5. **Winning glory** when the competition ends and standings freeze

### User Journey: From Registration to Victory

#### Act 1: Getting Started

```
1. User visits https://udl.app
   ↓
2. Sees Login page (frontend/src/pages/Login.tsx)
   - Clean form with email + password
   - "Don't have an account?" link to register
   ↓
3. Clicks "Sign up" → Register page (frontend/src/pages/Register.tsx)
   - Email, username, password, confirm password
   - Client-side validation (min length, matching passwords)
   ↓
4. Submits form → POST /api/auth/register
   ↓
5. Backend (backend/app/api/auth.py):
   - Validates email not taken
   - Validates username not taken
   - Hashes password with bcrypt
   - Creates User record (status=ACTIVE)
   - Generates JWT access token (30min) + refresh token (7 days)
   ↓
6. Frontend stores tokens in localStorage
   - useAuthStore updates: {user, isAuthenticated: true}
   ↓
7. Redirects to Dashboard (/)
```

#### Act 2: Creating a Competition

```
1. User clicks "Browse Competitions" in nav
   ↓
2. Competitions page (frontend/src/pages/Competitions.tsx)
   - Fetches GET /api/competitions
   - Shows grid of all accessible competitions
   - Each card: name, mode, status badge, participant count
   ↓
3. User clicks "Create Competition" button (TODO UI)
   ↓
4. Competition creation form appears (TODO):
   - Name: "NFL Season 2025"
   - League: NFL (dropdown)
   - Mode: Daily Picks or Fixed Teams
   - Date range: Sept 1 - Jan 31
   - Visibility: Public or Private
   - Join type: Open or Requires Approval
   - Max picks per day: 3 (for daily picks)
   ↓
5. Submits → POST /api/competitions
   ↓
6. Backend (backend/app/api/competitions.py):
   - Validates dates (end > start)
   - Creates Competition record (status=UPCOMING)
   - Auto-adds creator as Participant
   - Adds creator to league_admin_ids array
   ↓
7. Returns CompetitionResponse with:
   - participant_count: 1
   - user_is_participant: true
   - user_is_admin: true
   ↓
8. Frontend shows success, redirects to competition detail
```

#### Act 3: Daily Picks Game Mode

```
1. User navigates to competition detail
   ↓
2. CompetitionDetail page (frontend/src/pages/CompetitionDetail.tsx)
   - Fetches GET /api/competitions/{id}
   - Fetches GET /api/leaderboards/{id}
   - Shows competition header with metadata
   - Shows leaderboard table (rank, username, points, accuracy)
   ↓
3. User sees "Daily Picks" section
   ↓
4. System fetches upcoming games (TODO: API not called yet):
   - Background job should have fetched schedule
   - Games stored in database with scheduled_start_time
   ↓
5. User selects predicted winner for each game:
   - Game: Chiefs vs. 49ers (Jan 15, 8:00 PM ET)
   - Pick: Chiefs
   - Clicks "Submit Pick"
   ↓
6. Frontend → POST /api/picks/{competition_id}/daily
   Body: {game_id, predicted_winner_team_id}
   ↓
7. Backend (backend/app/api/picks.py):
   - Validates user is participant ✓
   - Validates game exists ✓
   - Validates game not started (scheduled_start_time > now) ✓
   - Validates daily pick limit not exceeded ✓
   - Creates or updates Pick record:
     * is_locked: false
     * is_correct: null
     * points_earned: 0
   ↓
8. Returns PickResponse
   ↓
9. Frontend shows "Pick submitted!" confirmation
```

#### Act 4: Game Time (Automated)

```
SCHEDULED JOBS RUNNING IN BACKGROUND:

Job 1: lock_expired_picks() runs every 60 seconds
   ↓
1. Finds all games where:
   - scheduled_start_time <= now
   - Picks exist with is_locked=false
   ↓
2. Updates Pick records:
   - SET is_locked=true, locked_at=now
   ↓
3. Users can no longer edit their picks

Job 2: update_game_scores() runs every 60 seconds
   ↓
1. Finds all games with status=IN_PROGRESS or status=SCHEDULED
   ↓
2. Calls SportsDataService.get_live_scores(league)
   ↓
3. SportsDataService orchestrates multi-API failover:

   Step A: Check Redis cache (TTL: 60s)
   - Key: "live_scores:NFL"
   - If hit → return cached data

   Step B: Cache miss → Try APIs in priority order

   Try ESPN API:
   ├─ Circuit breaker check (state: CLOSED?)
   ├─ HTTP GET to ESPN API
   ├─ Parse response → List[GameData]
   ├─ Cache in Redis (60s TTL)
   └─ Return

   If ESPN fails (rate limit, timeout, error):
   ├─ Circuit breaker records failure (count: 1/5)
   └─ Try The Odds API

   Try The Odds API:
   ├─ Circuit breaker check
   ├─ HTTP GET to The Odds API
   └─ Success → Cache → Return

   If The Odds fails:
   └─ Try RapidAPI (tertiary fallback)

   If ALL APIs fail:
   ├─ Log error
   ├─ Check for stale cache (expired but exists)
   └─ Return stale data if available

   ↓
4. For each game in response:
   - Update Game record:
     * status: "in_progress" or "final"
     * home_team_score: 24
     * away_team_score: 21
     * winner_team_id: home_team_id (if final)

   ↓
5. If game status=FINAL:
   - Find all Pick records for this game
   - For each pick:
     * is_correct = (predicted_winner_team_id == game.winner_team_id)
     * points_earned = 1 if is_correct else 0

   ↓
6. Aggregate scores per participant:
   - SELECT user_id, SUM(points_earned) as total_points
   - UPDATE Participant:
     * total_points
     * total_wins (count is_correct=true)
     * total_losses (count is_correct=false)
     * accuracy_percentage = (wins / total) * 100

   ↓
7. Invalidate leaderboard cache in Redis
   - DELETE key: "leaderboard:{competition_id}"
```

#### Act 5: Checking the Leaderboard

```
1. User refreshes competition detail page
   ↓
2. Frontend fetches GET /api/leaderboards/{competition_id}
   ↓
3. Backend (backend/app/api/leaderboards.py):
   - Queries Participant + User joined
   - Orders by total_points DESC
   - Calculates rank in Python (⚠️ should use SQL ROW_NUMBER)
   - Returns LeaderboardEntry array:
     [
       {rank: 1, username: "alice", total_points: 45, accuracy: 89.2%},
       {rank: 2, username: "bob", total_points: 43, accuracy: 87.5%},
       {rank: 3, username: "charlie", total_points: 40, accuracy: 85.1%, is_current_user: true}
     ]
   ↓
4. Frontend displays updated leaderboard
   - Highlights current user's row in blue
   - Shows rank change indicators (TODO)
```

#### Act 6: Competition Ends

```
Job: update_competition_statuses() runs every 5 minutes
   ↓
1. Checks all competitions where:
   - status=ACTIVE
   - end_date <= now
   - All associated games have status=FINAL
   ↓
2. Updates Competition:
   - SET status=COMPLETED
   ↓
3. Standings are now frozen (read-only)
   ↓
4. If multiple users tied for #1:
   - Leaderboard shows co-leaders
   - Admin can manually set winner_user_id
   - Spec says: coin flip in person (not automated)
```

### Fixed Teams Mode: The Alternative

```
Flow for Fixed Teams (e.g., PGA tournament):

1. User creates competition with mode=FIXED_TEAMS
   - max_golfers_per_participant: 5
   ↓
2. Before start_date, users select golfers:
   - POST /api/picks/{competition_id}/fixed
   - Body: {golfer_id: "tiger-woods-uuid"}
   ↓
3. Backend validates:
   - Competition not yet started ✓
   - User hasn't exceeded max_golfers ✓
   - Golfer not already selected by another user ✓ (exclusivity)
   ↓
4. Creates FixedTeamSelection record:
   - is_locked: false
   - total_points: 0
   ↓
5. On competition start_date:
   - Background job locks all FixedTeamSelection (is_locked=true)
   ↓
6. As tournament progresses:
   - Background job fetches PGA leaderboard
   - Awards points based on golfer performance:
     * 1st place: 10 points
     * 2nd place: 8 points
     * 3rd place: 6 points
     * etc.
   - Updates FixedTeamSelection.total_points
   ↓
7. Aggregates per user:
   - Participant.total_points = SUM(fixed_selections.total_points)
   ↓
8. Leaderboard shows standings
```

---

## 🔧 Module-by-Module Breakdown

### Backend Modules

#### 1. Core Module (`backend/app/core/`)

**Purpose:** Foundation layer providing configuration, security, and dependency injection

##### `config.py` - The Brain of Configuration
```python
class Settings(BaseSettings):
    """
    Single source of truth for all application settings.
    Uses Pydantic to validate and load from .env file.
    """

    # Database
    DATABASE_URL: str  # postgresql://user:pass@host:5432/db

    # Redis
    REDIS_URL: str  # redis://host:6379/0

    # Security (JWT)
    SECRET_KEY: str  # Strong random key for signing tokens
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS (Frontend URLs allowed to call API)
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Sports Data APIs (Multi-provider for redundancy)
    ESPN_API_KEY: str = ""
    THE_ODDS_API_KEY: str = ""
    RAPIDAPI_KEY: str = ""
    # ... plus MLB, NHL, PGA APIs

    # Circuit Breaker (Fault tolerance)
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5  # Trip after 5 failures
    CIRCUIT_BREAKER_TIMEOUT_SECONDS: int = 60   # Stay open for 60s

    # Caching TTLs
    CACHE_SCORES_SECONDS: int = 60        # Live scores change fast
    CACHE_LEADERBOARD_SECONDS: int = 30   # Leaderboards update frequently
    CACHE_SCHEDULE_SECONDS: int = 3600    # Schedules are stable

    # Background Jobs
    SCORE_UPDATE_INTERVAL_SECONDS: int = 60  # Poll every minute

settings = Settings()  # Global singleton
```

**Why it matters:**
- **Type safety:** Pydantic validates all settings at startup
- **Environment agnostic:** Same code works in dev/staging/prod with different .env
- **Documentation:** All settings in one place with defaults
- **Easy testing:** Can override settings in tests

##### `security.py` - Authentication Engine
```python
# Password Hashing with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Hashes password with bcrypt (cost factor 12).
    Takes ~100ms to hash, making brute force attacks impractical.
    """
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """
    Constant-time comparison to prevent timing attacks.
    """
    return pwd_context.verify(plain, hashed)

# JWT Token Management
def create_access_token(data: dict) -> str:
    """
    Creates short-lived access token (30 minutes).
    Token structure:
    {
      "sub": "user-uuid",      # Subject (who the token is for)
      "exp": 1234567890,       # Expiration timestamp
      "type": "access"         # Token type
    }
    Signed with HMAC-SHA256 using SECRET_KEY.
    """
    expire = datetime.utcnow() + timedelta(minutes=30)
    payload = {**data, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def create_refresh_token(data: dict) -> str:
    """
    Creates long-lived refresh token (7 days).
    Used to obtain new access tokens without re-login.
    """
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {**data, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str, token_type: str) -> Optional[dict]:
    """
    Verifies JWT signature and expiration.
    Returns payload if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None
```

**Security considerations:**
- **bcrypt cost factor 12:** Industry standard, ~100ms per hash
- **JWT vs sessions:** Stateless, scales horizontally
- **Token types:** Prevents access tokens being used as refresh tokens
- **Short access token TTL:** Limits damage if token is stolen
- **No token refresh endpoint:** Would require implementing (TODO)

##### `deps.py` - Dependency Injection Hub
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides database session.

    Usage:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()

    Lifecycle:
    1. Request starts → create new session
    2. Handler executes → session available
    3. Request ends → session closed (even if exception)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts and validates JWT token.

    Steps:
    1. Extract "Authorization: Bearer <token>" header
    2. Verify JWT signature and expiration
    3. Extract user_id from payload
    4. Fetch User from database
    5. Verify account is active
    6. Return User object

    Raises HTTPException(401) if invalid/missing token.
    Raises HTTPException(403) if account not active.
    """
    token = credentials.credentials
    payload = verify_token(token, "access")

    if not payload:
        raise HTTPException(401, "Invalid credentials")

    user_id = payload.get("sub")
    user = await db.get(User, user_id)

    if not user or user.status != "active":
        raise HTTPException(403, "Account not active")

    return user

async def get_current_global_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires global admin role.
    Chains on get_current_user, so JWT is validated first.

    Usage:
        @router.delete("/users/{id}")
        async def delete_user(
            admin: User = Depends(get_current_global_admin)
        ):
            # Only global admins can reach here
    """
    if current_user.role != UserRole.GLOBAL_ADMIN:
        raise HTTPException(403, "Global admin required")
    return current_user
```

**Why dependency injection?**
- **Testability:** Easy to mock dependencies in tests
- **Reusability:** Same auth logic in all endpoints
- **Declarative:** FastAPI automatically calls dependencies
- **Type safety:** MyPy knows `current_user` is a User object

---

#### 2. Data Layer (`backend/app/models/` + `backend/app/db/`)

**Purpose:** Database schema definition and ORM configuration

##### Database Architecture

```
PostgreSQL 15+ (chosen for JSONB, UUID, async support)
    ↓
asyncpg driver (pure Python, fastest async driver)
    ↓
SQLAlchemy 2.0 ORM (async API)
    ↓
Alembic (migrations, not yet generated)
```

##### `db/session.py` - Connection Pool Manager
```python
# Convert postgresql:// to postgresql+asyncpg://
database_url = settings.DATABASE_URL.replace(
    "postgresql://",
    "postgresql+asyncpg://"
)

# Create async engine with connection pooling
engine = create_async_engine(
    database_url,
    echo=True if development else False,  # Log SQL queries in dev
    future=True,  # Use SQLAlchemy 2.0 API
    pool_size=10,  # Max 10 connections in pool
    max_overflow=20,  # Allow 20 additional connections under load
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
)

Base = declarative_base()  # All models inherit from this
```

**Connection pool benefits:**
- **Reuse:** Connections are expensive to create (~100ms), pool reuses them
- **Concurrency:** Handle 30 concurrent requests with 10 connections
- **Overflow:** Temporarily create more connections under heavy load

##### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER (auth)                            │
│  • email, username, hashed_password                             │
│  • role: user|league_admin|global_admin                         │
│  • status: active|pending_deletion|deleted                      │
└───────┬─────────────────────────────────────┬───────────────────┘
        │                                     │
        │ creates                             │ participates
        ▼                                     ▼
┌──────────────────┐                 ┌─────────────────┐
│   COMPETITION    │◄────────────────┤   PARTICIPANT   │
│  • mode          │  belongs to     │  • total_points │
│  • status        │                 │  • accuracy_%   │
│  • start/end     │                 └─────────────────┘
│  • max_picks     │                          │
└────┬─────────────┘                          │ scores for
     │                                        ▼
     │ has games            ┌──────────────────────────┐
     ▼                      │         PICK             │
┌──────────────────┐        │  • predicted_winner     │
│      GAME        │◄───────┤  • is_locked            │
│  • external_id   │  for   │  • is_correct           │
│  • home/away     │        │  • points_earned        │
│  • scores        │        └──────────────────────────┘
│  • status        │
│  • winner        │                    OR
└────┬─────────────┘
     │                      ┌──────────────────────────┐
     │ played by            │  FIXEDTEAMSELECTION      │
     ▼                      │  • team_id | golfer_id   │
┌──────────────────┐        │  • is_locked             │
│   TEAM/GOLFER    │◄───────┤  • total_points          │
│  • external_id   │  uses  └──────────────────────────┘
│  • name          │
│  • league        │
└──────────────────┘
        ▲
        │ belongs to
        │
┌──────────────────┐
│     LEAGUE       │
│  • NFL, NBA, ... │
│  • is_team_based │
└──────────────────┘
```

##### Key Models Explained

**User Model** - Authentication and Roles
```python
class User(Base):
    """
    Central user entity. One user can:
    - Create many competitions (creator_id)
    - Participate in many competitions (via Participant)
    - Make many picks (via Pick)
    - Have one of three roles:
      * USER: Regular participant
      * LEAGUE_ADMIN: Can manage specific competitions
      * GLOBAL_ADMIN: Full system access
    """
    id: UUID
    email: str (unique, for login)
    username: str (unique, for display)
    hashed_password: str (bcrypt hash)
    role: UserRole (enum)
    status: AccountStatus (enum)

    # Account deletion workflow
    deletion_requested_at: datetime | None
    # After 30 days, background job permanently deletes
```

**Competition Model** - Contest Orchestration
```python
class Competition(Base):
    """
    Central entity representing a prediction contest.

    Two modes:
    1. DAILY_PICKS: Pick game winners, lock at game time
    2. FIXED_TEAMS: Pre-select teams/golfers, accumulate points

    Three statuses (lifecycle):
    1. UPCOMING: Not started, users can join, make future picks
    2. ACTIVE: Games happening, picks lock, scores update
    3. COMPLETED: All games finished, standings frozen
    """
    mode: CompetitionMode
    status: CompetitionStatus

    # Dates define lifecycle
    start_date: datetime  # When competition becomes ACTIVE
    end_date: datetime    # Last game date

    # Access control
    visibility: PUBLIC | PRIVATE
    join_type: OPEN | REQUIRES_APPROVAL

    # Admin array (⚠️ should be junction table)
    league_admin_ids: Array[UUID]
    # These users can approve joins, adjust settings
```

**Game Model** - Individual Match
```python
class Game(Base):
    """
    Represents a single sporting event.
    Synced from external APIs (ESPN, The Odds, etc.)

    Lifecycle:
    1. Created by background job fetching schedule
    2. Status: SCHEDULED
    3. Game starts → Status: IN_PROGRESS
    4. Game ends → Status: FINAL, winner_team_id set
    5. Picks are scored
    """
    external_id: str  # ID from sports API (e.g., "ESPN-123")
    home_team_id: UUID
    away_team_id: UUID
    scheduled_start_time: datetime (UTC)
    status: GameStatus
    home_team_score: int | None
    away_team_score: int | None
    winner_team_id: UUID | None

    # Raw API response stored for debugging
    api_data: JSON
```

**Pick Model** - Daily Predictions
```python
class Pick(Base):
    """
    User's prediction for a single game.

    Lifecycle:
    1. User submits pick (is_locked=false)
    2. User can edit pick until game starts
    3. Game starts → Background job sets is_locked=true
    4. Game ends → Background job scores pick:
       - is_correct = (predicted == winner)
       - points_earned = 1 if correct else 0
    5. Participant totals updated
    """
    user_id: UUID
    game_id: UUID
    competition_id: UUID
    predicted_winner_team_id: UUID

    is_locked: bool (prevents editing)
    locked_at: datetime | None

    is_correct: bool | None (null until scored)
    points_earned: int (0 or 1)

    # Constraint: One pick per user per game per competition
```

**Participant Model** - Scoring Aggregation
```python
class Participant(Base):
    """
    Links a user to a competition with aggregated stats.
    Denormalized for performance (leaderboard queries).

    Updated by background jobs after scoring picks.
    """
    user_id: UUID
    competition_id: UUID

    # Aggregated stats (calculated, not entered)
    total_points: int
    total_wins: int
    total_losses: int
    accuracy_percentage: float
    current_streak: int (consecutive correct picks)

    joined_at: datetime
    last_pick_at: datetime | None
```

##### Indexing Strategy

```sql
-- Primary indexes (all UUIDs have default indexes)

-- Foreign key indexes (for joins)
CREATE INDEX idx_pick_user_id ON picks(user_id);
CREATE INDEX idx_pick_game_id ON picks(game_id);
CREATE INDEX idx_pick_competition_id ON picks(competition_id);

-- Status indexes (for filtering)
CREATE INDEX idx_competition_status ON competitions(status);
CREATE INDEX idx_game_status ON games(status);
CREATE INDEX idx_pick_locked ON picks(is_locked);

-- Date indexes (for time-based queries)
CREATE INDEX idx_game_start_time ON games(scheduled_start_time);
CREATE INDEX idx_competition_dates ON competitions(start_date, end_date);

-- Leaderboard indexes
CREATE INDEX idx_participant_points ON participants(total_points DESC);

-- ⚠️ MISSING: Composite indexes for common queries
-- TODO: Add these for better performance
CREATE INDEX idx_pick_user_comp ON picks(user_id, competition_id);
CREATE INDEX idx_game_comp_status ON games(competition_id, status);
CREATE INDEX idx_participant_comp_points ON participants(competition_id, total_points DESC);
```

---

#### 3. API Layer (`backend/app/api/`)

**Purpose:** HTTP endpoint handlers with request validation and response formatting

##### API Router Architecture

```
FastAPI App (main.py)
    ├─── /api/auth         → auth.py (public)
    ├─── /api/users        → users.py (authenticated)
    ├─── /api/competitions → competitions.py (authenticated)
    ├─── /api/picks        → picks.py (authenticated)
    ├─── /api/leaderboards → leaderboards.py (authenticated)
    ├─── /api/admin        → admin.py (admin only)
    └─── /api/health       → health.py (monitoring)
```

##### REST API Conventions

All endpoints follow consistent patterns:

1. **Authentication:** JWT bearer token in `Authorization` header
2. **Request validation:** Pydantic schemas validate input
3. **Response format:** Consistent JSON structure
4. **Error handling:** HTTPException with appropriate status codes
5. **Async operations:** All handlers are async for performance

##### `api/auth.py` - Authentication Flow

```python
@router.post("/register")
async def register(user_data: UserCreate, db: AsyncSession):
    """
    Registration workflow:

    1. Validate input (Pydantic):
       - email: Valid email format
       - username: 3-50 chars
       - password: Min 8 chars

    2. Check uniqueness:
       - Query User by email
       - Query User by username
       - Raise 400 if either exists

    3. Create user:
       - Hash password with bcrypt
       - Create User(status=ACTIVE)
       - Insert to database

    4. Generate tokens:
       - Access token (30 min)
       - Refresh token (7 days)

    5. Return:
       - Tokens
       - User object (without password)
    """

@router.post("/login")
async def login(credentials: UserLogin, db: AsyncSession):
    """
    Login workflow:

    1. Find user by email
    2. Verify password (constant-time comparison)
    3. Check status=ACTIVE
    4. Update last_login_at
    5. Generate tokens
    6. Return tokens + user

    Security:
    - Constant-time password verification (prevents timing attacks)
    - Generic error message (doesn't reveal if email exists)
    - Rate limiting (TODO: not implemented yet)
    """
```

##### `api/competitions.py` - Competition Management

```python
@router.post("")
async def create_competition(
    data: CompetitionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates competition and auto-joins creator.

    Validation:
    - end_date > start_date
    - league_id exists
    - max_picks_per_day if mode=DAILY_PICKS
    - max_teams_per_participant if mode=FIXED_TEAMS

    Side effects:
    - Creates Competition (status=UPCOMING)
    - Creates Participant for creator
    - Adds creator to league_admin_ids

    Returns:
    - Full competition details
    - participant_count: 1
    - user_is_admin: true
    """

@router.get("")
async def list_competitions(
    status_filter: Optional[CompetitionStatus] = None,
    visibility: Optional[Visibility] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists competitions visible to user.

    Visibility logic:
    - PUBLIC: Everyone can see
    - PRIVATE: Only participants can see

    Query optimization:
    - Subquery: user's competition IDs (via Participant)
    - WHERE: visibility=PUBLIC OR id IN (user's competitions)

    ⚠️ Missing: Pagination (returns all results)
    TODO: Add limit/offset parameters
    """

@router.post("/{id}/join")
async def join_competition(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Join competition workflow.

    If join_type=OPEN:
    1. Check max_participants not exceeded
    2. Create Participant immediately
    3. Return success

    If join_type=REQUIRES_APPROVAL:
    1. Check no existing JoinRequest
    2. Create JoinRequest(status=PENDING)
    3. Admin must approve via /api/admin/join-requests
    """
```

##### `api/picks.py` - Pick Submission

```python
@router.post("/{competition_id}/daily")
async def create_daily_pick(
    competition_id: str,
    pick_data: PickCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Daily pick submission with extensive validation.

    Validation steps:
    1. Competition exists and mode=DAILY_PICKS ✓
    2. User is participant ✓
    3. Game exists and belongs to competition ✓
    4. Game not started (scheduled_start_time > now) ✓
    5. Predicted team is actually in the game ✓
    6. Daily pick limit not exceeded (if set) ✓

    Upsert logic:
    - If pick exists for this game: UPDATE
    - Else: INSERT new pick

    Lock check:
    - Cannot edit if is_locked=true
    - Background job locks picks when game starts
    """

@router.post("/{competition_id}/fixed")
async def create_fixed_team_selection(
    competition_id: str,
    data: FixedTeamSelectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fixed team selection with exclusivity enforcement.

    Validation:
    1. Competition mode=FIXED_TEAMS ✓
    2. Competition not started (start_date > now) ✓
    3. User is participant ✓
    4. Must provide team_id XOR golfer_id ✓
    5. Team/golfer belongs to competition's league ✓
    6. Max selections not exceeded ✓
    7. Team/golfer not already selected (EXCLUSIVITY) ✓

    Exclusivity query:
    SELECT COUNT(*) FROM fixed_team_selections
    WHERE competition_id = ? AND (team_id = ? OR golfer_id = ?)

    If count > 0: Raise 400 "Already selected by another user"
    """
```

##### `api/leaderboards.py` - Ranking Calculation

```python
@router.get("/{competition_id}")
async def get_leaderboard(
    competition_id: str,
    sort_by: str = Query("points", regex="^(points|accuracy|wins|streak)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Leaderboard with dynamic sorting.

    Current implementation (⚠️ NEEDS OPTIMIZATION):
    1. Query: Participant JOIN User
    2. Sort by: total_points DESC (or other field)
    3. Fetch all participants
    4. Calculate rank in Python loop (rank = 1, 2, 3...)
    5. Return list

    Problems:
    - Rank calculated in Python (should use SQL)
    - Doesn't handle ties properly (both rank 1 or both rank 2?)
    - No pagination (returns all participants)

    Better approach (TODO):
    SELECT
      ROW_NUMBER() OVER (ORDER BY total_points DESC) as rank,
      user_id, username, total_points, ...
    FROM participants
    JOIN users ON users.id = participants.user_id
    WHERE competition_id = ?
    ORDER BY total_points DESC
    LIMIT 50 OFFSET ?

    Tie handling options:
    - ROW_NUMBER(): 1, 2, 3 (sequential)
    - RANK(): 1, 1, 3 (skip next rank)
    - DENSE_RANK(): 1, 1, 2 (no skip)

    Spec says: Ties resolved by coin flip (manual)
    """
```

##### `api/admin.py` - Administrative Functions

```python
@router.post("/join-requests/{request_id}/approve")
async def approve_join_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Join request approval workflow.

    Authorization check:
    1. Get JoinRequest
    2. Get Competition
    3. Check: current_user.id in league_admin_ids OR role=GLOBAL_ADMIN
    4. If not admin: Raise 403

    ⚠️ Code duplication: This check appears in multiple endpoints
    TODO: Create get_competition_admin() dependency

    Side effects:
    1. Update JoinRequest:
       - status=APPROVED
       - reviewed_by_user_id=current_user.id
       - reviewed_at=now

    2. Create Participant:
       - user_id=request.user_id
       - competition_id=request.competition_id

    3. Create AuditLog:
       - action=JOIN_REQUEST_APPROVED
       - admin_user_id=current_user.id
       - details={competition_id, user_id}
    """

@router.get("/audit-logs")
async def get_audit_logs(
    competition_id: Optional[str] = None,
    action_filter: Optional[AuditAction] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Audit log retrieval with permission filtering.

    Global admin: Sees all logs
    League admin: Sees logs for competitions they manage
    Regular user: 403 Forbidden

    Filtering:
    - If not global admin:
      1. Query competitions where user in league_admin_ids
      2. Filter logs by those competition IDs

    - Apply competition_id filter if provided
    - Apply action filter if provided
    - Order by created_at DESC
    - Paginate with limit/offset

    Returns: List of audit log entries with full details
    """
```

##### `api/health.py` - Monitoring and Diagnostics

```python
@router.get("/api-status")
async def get_api_status(current_user: User = Depends(get_current_user)):
    """
    Returns health status of all sports data providers.

    Response:
    {
      "configured_apis": ["ESPN", "TheOddsAPI", "RapidAPI"],
      "circuit_breakers": {
        "espn_schedule": {
          "state": "closed",
          "failure_count": 0,
          "last_success": "2025-01-11T10:30:00Z"
        },
        "theodds_live_scores": {
          "state": "open",
          "failure_count": 5,
          "last_failure": "2025-01-11T10:25:00Z",
          "time_until_reset": 45
        }
      },
      "cache_status": "connected"
    }

    Use cases:
    - Debugging: Why are scores not updating?
    - Monitoring: Which API is down?
    - Operations: Should we reset circuit breakers?
    """

@router.post("/reset-circuit-breakers")
async def reset_circuit_breakers(
    admin: User = Depends(get_current_global_admin)
):
    """
    Manually reset all circuit breakers.
    Global admin only.

    Use case: API was temporarily down, now back up,
    but circuit breakers are still open.

    Side effects:
    - All circuit breakers: state=CLOSED, failure_count=0
    - Next API call will attempt connection
    """
```

---

#### 4. Service Layer (`backend/app/services/`)

**Purpose:** Business logic, external integrations, and background processing

##### `services/sports_api/` - Multi-API Failover System

This is the **most complex and critical** part of the backend.

**Architecture Overview:**

```
┌─────────────────────────────────────────────────────────────┐
│                    SportsDataService                        │
│                   (Orchestrator/Facade)                     │
│                                                             │
│  Methods:                                                   │
│  - get_schedule(league, start, end)                        │
│  - get_live_scores(league)                                 │
│  - get_game_details(league, game_id)                       │
│                                                             │
│  Responsibilities:                                          │
│  - Try APIs in priority order                              │
│  - Cache results in Redis                                  │
│  - Fall back to stale cache if all fail                    │
│  - Wrap each API call in circuit breaker                   │
└────┬────────────────────────────────────────────────────────┘
     │
     ├──────────────┬──────────────┬──────────────┐
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│  ESPN   │   │  Odds   │   │ RapidAPI│   │  Free   │
│  Client │   │  Client │   │ Client  │   │  APIs   │
│         │   │         │   │         │   │         │
│Priority │   │Priority │   │Priority │   │Priority │
│   #1    │   │   #2    │   │   #3    │   │   #4    │
└────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
     │             │             │             │
     └─────────────┴─────────────┴─────────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │  CircuitBreaker      │
               │  per API + operation │
               │                      │
               │  States:             │
               │  - CLOSED (normal)   │
               │  - OPEN (failing)    │
               │  - HALF_OPEN (test)  │
               └──────────────────────┘
```

##### `sports_service.py` - The Orchestrator

```python
class SportsDataService:
    """
    Coordinates multiple sports data providers with resilience.

    Key features:
    1. Priority-based failover (ESPN → Odds → RapidAPI)
    2. Circuit breaker per API (prevent hammering dead APIs)
    3. Redis caching (reduce API calls, improve latency)
    4. Stale cache fallback (serve old data if all APIs down)
    """

    def __init__(self):
        # Initialize clients in priority order
        self.clients: List[BaseSportsAPIClient] = []

        if settings.ESPN_API_KEY:
            self.clients.append(ESPNAPIClient())
        if settings.THE_ODDS_API_KEY:
            self.clients.append(TheOddsAPIClient())
        if settings.RAPIDAPI_KEY:
            self.clients.append(RapidAPIClient())

        # Connect to Redis for caching
        self.redis_client = redis.from_url(settings.REDIS_URL)

    async def get_live_scores(self, league: str) -> List[GameData]:
        """
        Fetch live scores with full resilience stack.

        Step 1: Check cache
        ─────────────────────
        cache_key = "live_scores:NFL"
        cached = redis.get(cache_key)
        if cached:
            return deserialize(cached)

        Step 2: Try APIs in priority order
        ───────────────────────────────────
        for client in [ESPN, Odds, RapidAPI]:
            try:
                # Get circuit breaker for this API + operation
                breaker = circuit_breaker_manager.get_breaker(
                    name=f"{client.provider}_live_scores",
                    failure_threshold=5,
                    timeout_seconds=60
                )

                # Check if circuit is open
                if breaker.state == OPEN:
                    if should_attempt_reset():
                        breaker.state = HALF_OPEN
                    else:
                        raise CircuitBreakerOpenError()

                # Execute API call
                games = await client.get_live_scores(league)

                # Success!
                breaker.on_success()  # Reset failure count

                # Cache result
                redis.setex(
                    cache_key,
                    ttl=60,  # Live scores change fast
                    value=serialize(games)
                )

                return games

            except RateLimitExceededError:
                breaker.on_failure()
                continue  # Try next API

            except httpx.HTTPError:
                breaker.on_failure()
                if breaker.failure_count >= 5:
                    breaker.trip()  # Open circuit
                continue

        Step 3: All APIs failed, try stale cache
        ─────────────────────────────────────────
        stale = redis.get(cache_key)  # Even if expired
        if stale:
            logger.warning("All APIs failed, returning stale cache")
            return deserialize(stale)

        Step 4: Give up
        ───────────────
        raise APIUnavailableError(
            "All sports data providers failed"
        )
        """
```

**Example: The Odds API Response**

```json
// GET https://api.the-odds-api.com/v4/sports/americanfootball_nfl/scores
[
  {
    "id": "abc123",
    "sport_key": "americanfootball_nfl",
    "sport_title": "NFL",
    "commence_time": "2025-01-15T20:00:00Z",
    "completed": false,
    "home_team": "Kansas City Chiefs",
    "away_team": "San Francisco 49ers",
    "scores": [
      {"name": "Kansas City Chiefs", "score": "24"},
      {"name": "San Francisco 49ers", "score": "21"}
    ],
    "last_update": "2025-01-15T22:30:00Z"
  }
]
```

**Transformation to GameData:**

```python
def parse_theodds_response(data) -> List[GameData]:
    games = []
    for item in data:
        game = GameData(
            external_id=item["id"],
            home_team=item["home_team"],
            away_team=item["away_team"],
            scheduled_start_time=parse_iso(item["commence_time"]),
            status="final" if item["completed"] else "in_progress",
            home_score=int(item["scores"][0]["score"]),
            away_score=int(item["scores"][1]["score"]),
            venue=None,
            raw_data=item  # Store original for debugging
        )
        games.append(game)
    return games
```

##### `circuit_breaker.py` - Fault Tolerance

```python
class CircuitBreaker:
    """
    Implements circuit breaker pattern (Netflix Hystrix style).

    Purpose: Prevent cascading failures by failing fast.

    Analogy: Electrical circuit breaker
    - Normal operation: Circuit CLOSED (electricity flows)
    - Fault detected: Circuit OPENS (stops electricity)
    - After timeout: Circuit HALF_OPEN (test if fault cleared)

    States:
    ┌──────────┐
    │  CLOSED  │  Normal operation, all calls allowed
    │          │  Tracks failures
    └────┬─────┘
         │ 5 failures
         ▼
    ┌──────────┐
    │   OPEN   │  Rejects all calls for 60 seconds
    │          │  Prevents hammering dead service
    └────┬─────┘
         │ 60s timeout
         ▼
    ┌──────────┐
    │ HALF_OPEN│  Allow ONE test call
    │          │  ├─ Success → CLOSED
    └──────────┘  └─ Failure → OPEN
    """

    def __init__(self, name: str, failure_threshold=5, timeout_seconds=60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Example usage:
        breaker = CircuitBreaker("espn_api")
        try:
            result = breaker.call(fetch_espn_scores, "NFL")
        except CircuitBreakerOpenError:
            # Circuit is open, don't even try
            return use_fallback()
        """

        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout_seconds):
                logger.info(f"{self.name}: Timeout passed, trying HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                # Still in timeout period
                time_left = self.timeout_seconds - (datetime.utcnow() - self.last_failure_time).seconds
                raise CircuitBreakerOpenError(
                    f"{self.name} is OPEN, retry in {time_left}s"
                )

        try:
            # Execute the function
            result = func(*args, **kwargs)

            # Success!
            self.failure_count = 0
            self.last_success_time = datetime.utcnow()

            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"{self.name}: Test call succeeded, CLOSING circuit")
                self.state = CircuitState.CLOSED

            return result

        except Exception as e:
            # Failure!
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()

            logger.warning(
                f"{self.name}: Failure {self.failure_count}/{self.failure_threshold}"
            )

            if self.failure_count >= self.failure_threshold:
                logger.error(f"{self.name}: TRIPPED - Opening circuit for {self.timeout_seconds}s")
                self.state = CircuitState.OPEN

            raise e

class CircuitBreakerManager:
    """
    Manages multiple circuit breakers (one per API + operation).

    Example breakers:
    - "espn_schedule"
    - "espn_live_scores"
    - "theodds_schedule"
    - "theodds_live_scores"
    - "rapidapi_schedule"

    Each is independent (ESPN schedule failing doesn't affect ESPN scores)
    """

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, name: str, failure_threshold=5, timeout_seconds=60) -> CircuitBreaker:
        """Get or create circuit breaker by name"""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name, failure_threshold, timeout_seconds)
        return self.breakers[name]

    def get_all_status(self) -> Dict[str, dict]:
        """Get status of all breakers (for /api/health/api-status)"""
        return {
            name: breaker.get_status()
            for name, breaker in self.breakers.items()
        }

# Global singleton
circuit_breaker_manager = CircuitBreakerManager()
```

**Real-world scenario:**

```
10:00 AM: ESPN API is healthy
- Circuit: CLOSED
- All requests succeed

10:15 AM: ESPN API starts timing out (their servers overloaded)
- Request 1: Timeout after 10s, failure_count=1
- Request 2: Timeout after 10s, failure_count=2
- Request 3: Timeout after 10s, failure_count=3
- Request 4: Timeout after 10s, failure_count=4
- Request 5: Timeout after 10s, failure_count=5
- Circuit TRIPS: state=OPEN

10:15:30 AM: Next request arrives
- Circuit is OPEN
- Immediately rejects (no API call made)
- Saves 10s timeout
- Falls back to The Odds API

10:16:30 AM: 60 seconds passed since trip
- Circuit: state=HALF_OPEN
- Next request allowed through
- ESPN API still down → Fails
- Circuit: state=OPEN (another 60s timeout)

10:20:00 AM: ESPN API recovers
- Circuit: state=HALF_OPEN (testing)
- Request succeeds
- Circuit: state=CLOSED (normal operation resumed)
```

##### `background_jobs.py` - Scheduled Tasks

```python
"""
Background jobs using APScheduler.

⚠️ Current issue: Uses BackgroundScheduler (synchronous)
TODO: Should use AsyncIOScheduler (asynchronous)

Jobs are defined but NOT IMPLEMENTED (stubs with TODO comments).
"""

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

async def update_game_scores():
    """
    Runs every 60 seconds.

    Purpose: Sync game scores from external APIs to database.

    Pseudocode:
    ──────────
    1. Query active games:
       SELECT * FROM games
       WHERE status IN ('scheduled', 'in_progress')
       AND scheduled_start_time <= NOW() + INTERVAL '2 hours'

    2. Group by league:
       nfl_games = [game for game in games if game.league == 'NFL']
       nba_games = [game for game in games if game.league == 'NBA']

    3. Fetch scores:
       nfl_scores = await sports_service.get_live_scores('NFL')
       nba_scores = await sports_service.get_live_scores('NBA')

    4. Match games by external_id:
       for game in nfl_games:
           score_data = find_by_external_id(nfl_scores, game.external_id)
           if score_data:
               game.home_team_score = score_data.home_score
               game.away_team_score = score_data.away_score
               game.status = score_data.status

               if game.status == 'final':
                   game.winner_team_id = (
                       game.home_team_id if score_data.home_score > score_data.away_score
                       else game.away_team_id
                   )

    5. Save updates:
       await db.commit()

    6. Score picks:
       for game in games where status changed to 'final':
           picks = SELECT * FROM picks WHERE game_id = game.id
           for pick in picks:
               pick.is_correct = (pick.predicted_winner_team_id == game.winner_team_id)
               pick.points_earned = 1 if pick.is_correct else 0

    7. Update participant totals:
       for competition_id in affected_competitions:
           participants = SELECT * FROM participants WHERE competition_id = ?
           for participant in participants:
               picks = SELECT * FROM picks
                       WHERE user_id = participant.user_id
                       AND competition_id = competition_id

               participant.total_points = SUM(picks.points_earned)
               participant.total_wins = COUNT(picks WHERE is_correct=true)
               participant.total_losses = COUNT(picks WHERE is_correct=false)
               participant.accuracy_percentage = (total_wins / total) * 100

    8. Invalidate caches:
       for competition_id in affected_competitions:
           redis.delete(f"leaderboard:{competition_id}")

    Status: 🔴 TODO - Not implemented yet
    """
    pass

async def update_competition_statuses():
    """
    Runs every 5 minutes.

    Purpose: Transition competitions through lifecycle.

    Transitions:
    ────────────
    UPCOMING → ACTIVE:
    - Conditions: start_date <= NOW()
    - Actions:
      * SET status = 'active'
      * Lock all FixedTeamSelection (is_locked=true)

    ACTIVE → COMPLETED:
    - Conditions:
      * end_date <= NOW()
      * All associated games have status='final'
    - Actions:
      * SET status = 'completed'
      * Standings are now frozen

    Query:
    ──────
    # Find competitions to activate
    SELECT * FROM competitions
    WHERE status = 'upcoming'
    AND start_date <= NOW()

    # Find competitions to complete
    SELECT * FROM competitions
    WHERE status = 'active'
    AND end_date <= NOW()
    AND NOT EXISTS (
        SELECT 1 FROM games
        WHERE competition_id = competitions.id
        AND status NOT IN ('final', 'cancelled', 'no_result')
    )

    Status: 🔴 TODO - Not implemented yet
    """
    pass

async def lock_expired_picks():
    """
    Runs every 60 seconds.

    Purpose: Lock picks for games that have started.

    Query:
    ──────
    UPDATE picks
    SET is_locked = true, locked_at = NOW()
    WHERE is_locked = false
    AND game_id IN (
        SELECT id FROM games
        WHERE scheduled_start_time <= NOW()
    )

    This prevents users from editing picks after game starts.

    Status: 🔴 TODO - Not implemented yet
    """
    pass

async def cleanup_pending_deletions():
    """
    Runs daily at 2 AM UTC.

    Purpose: Permanently delete accounts after 30-day grace period.

    Workflow:
    ─────────
    1. Find users to delete:
       SELECT * FROM users
       WHERE status = 'pending_deletion'
       AND deletion_requested_at <= NOW() - INTERVAL '30 days'

    2. For each user:
       a. Anonymize data:
          user.email = f"deleted_{uuid4()}@deleted.com"
          user.username = f"deleted_{uuid4()}"
          user.hashed_password = "DELETED"

       b. Update status:
          user.status = 'deleted'

       c. Keep records for data integrity:
          - Don't delete Participant records
          - Don't delete Pick records
          - Don't delete AuditLog entries
          - User shows as "Deleted User" in UI

    Status: 🔴 TODO - Not implemented yet
    """
    pass

def start_background_jobs():
    """
    Called on application startup (main.py:lifespan).
    Registers all jobs with scheduler.
    """
    scheduler.add_job(
        update_game_scores,
        trigger=IntervalTrigger(seconds=60),
        id="update_game_scores",
        replace_existing=True
    )

    scheduler.add_job(
        update_competition_statuses,
        trigger=IntervalTrigger(minutes=5),
        id="update_competition_statuses",
        replace_existing=True
    )

    scheduler.add_job(
        lock_expired_picks,
        trigger=IntervalTrigger(seconds=60),
        id="lock_expired_picks",
        replace_existing=True
    )

    scheduler.add_job(
        cleanup_pending_deletions,
        trigger="cron",
        hour=2,
        minute=0,
        id="cleanup_pending_deletions",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Background jobs started")

def stop_background_jobs():
    """
    Called on application shutdown.
    Gracefully stops scheduler.
    """
    scheduler.shutdown()
    logger.info("Background jobs stopped")
```

---

### Frontend Modules

#### 1. Entry Points

##### `main.tsx` - React Bootstrap

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

// TanStack Query configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,  // 5 minutes
      refetchOnWindowFocus: false,
      retry: 1
    }
  }
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
)
```

**What's happening:**
- **React 18 StrictMode:** Helps catch bugs in development
- **TanStack Query:** Manages server state (caching, refetching, invalidation)
- **BrowserRouter:** Enables client-side routing (no page reloads)
- **staleTime: 5min:** Cached data considered fresh for 5 minutes
- **refetchOnWindowFocus: false:** Don't refetch when switching tabs (annoying UX)
- **retry: 1:** Retry failed requests once (balance between reliability and speed)

##### `App.tsx` - Router and Auth Guards

```tsx
function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" /> : <Login />}
      />
      <Route
        path="/register"
        element={isAuthenticated ? <Navigate to="/" /> : <Register />}
      />

      {/* Protected routes with layout */}
      <Route element={<Layout />}>
        <Route
          path="/"
          element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route
          path="/competitions"
          element={isAuthenticated ? <Competitions /> : <Navigate to="/login" />}
        />
        <Route
          path="/competitions/:id"
          element={isAuthenticated ? <CompetitionDetail /> : <Navigate to="/login" />}
        />
      </Route>
    </Routes>
  )
}
```

**Auth guard pattern:**
- **Public routes (login, register):** Redirect to dashboard if already logged in
- **Protected routes:** Redirect to login if not authenticated
- **Layout wrapper:** Nested routes render inside `<Layout>` (shared nav/footer)

---

#### 2. State Management

##### `services/authStore.ts` - Zustand Auth Store

```typescript
interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,

  // Initialize from localStorage (survives page refresh)
  isAuthenticated: !!localStorage.getItem('access_token'),

  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password })
    const { access_token, refresh_token, user } = response.data

    // Store tokens (⚠️ XSS vulnerable if script injection)
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)

    // Update store
    set({ user, isAuthenticated: true })
  },

  register: async (email, username, password) => {
    const response = await api.post('/auth/register', {
      email, username, password
    })
    const { access_token, refresh_token, user } = response.data

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)

    set({ user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false })
  },

  checkAuth: async () => {
    try {
      if (localStorage.getItem('access_token')) {
        const response = await api.get('/users/me')
        set({ user: response.data, isAuthenticated: true })
      }
    } catch (error) {
      // Token invalid/expired
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, isAuthenticated: false })
    }
  }
}))
```

**Zustand benefits:**
- **Lightweight:** <1KB, no boilerplate
- **Reactive:** Components auto-rerender on state changes
- **DevTools:** Browser extension for debugging
- **Async actions:** Promises work naturally

**Security considerations:**
- ⚠️ **localStorage XSS risk:** If attacker injects script, can steal tokens
- ✅ **Alternative:** httpOnly cookies (immune to XSS, vulnerable to CSRF)
- ⚠️ **No token refresh:** Access token expires after 30min, user logged out
- TODO: Implement silent refresh with refresh token

##### `services/api.ts` - Axios HTTP Client

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { 'Content-Type': 'application/json' }
})

// Interceptor: Inject JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor: Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token invalid/expired
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'  // ⚠️ Hard-coded redirect
    }
    return Promise.reject(error)
  }
)
```

**Interceptor pattern:**
- **Request interceptor:** Runs before every request (add auth header)
- **Response interceptor:** Runs after every response (handle errors)
- **Automatic auth:** No need to manually add token to each request

**Issues:**
- ⚠️ **Hard-coded redirect:** Should emit event, let router handle
- ⚠️ **No retry logic:** If request fails, gives up immediately
- ⚠️ **No request cancellation:** Switching pages leaves pending requests

---

#### 3. Pages

##### `pages/Login.tsx` - Authentication Form

```tsx
export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const { login } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(email, password)
      navigate('/')  // Redirect to dashboard
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="card max-w-md w-full">
        <h1 className="text-3xl font-bold mb-6">Sign In</h1>

        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label>Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input"
            />
          </div>

          <div>
            <label>Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="mt-4 text-center">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary-600">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
```

**Status:** ✅ Fully implemented
**Features:**
- Form validation (HTML5 required)
- Error display (API error messages)
- Loading state (prevents double-submit)
- Accessible (labels, ARIA)
- Mobile responsive (Tailwind)

##### `pages/Dashboard.tsx` - Home View

```tsx
export default function Dashboard() {
  const { data: competitions, isLoading } = useQuery({
    queryKey: ['competitions'],
    queryFn: async () => {
      const response = await api.get('/competitions')
      return response.data
    }
  })

  if (isLoading) {
    return <div className="text-center py-8">Loading...</div>
  }

  // Filter by status
  const activeCompetitions = competitions?.filter(
    (c: any) => c.status === 'active'
  ) || []

  const upcomingCompetitions = competitions?.filter(
    (c: any) => c.status === 'upcoming'
  ) || []

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Link to="/competitions" className="btn btn-primary">
          Browse Competitions
        </Link>
      </div>

      {/* Empty state */}
      {activeCompetitions.length === 0 && upcomingCompetitions.length === 0 && (
        <div className="card text-center py-12">
          <h2 className="text-xl font-semibold mb-4">
            You haven't joined any competitions yet
          </h2>
          <Link to="/competitions" className="btn btn-primary">
            Browse Competitions
          </Link>
        </div>
      )}

      {/* Active competitions */}
      {activeCompetitions.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-4">Active Competitions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeCompetitions.map((comp: any) => (
              <Link
                key={comp.id}
                to={`/competitions/${comp.id}`}
                className="card hover:shadow-lg transition"
              >
                <h3 className="font-semibold">{comp.name}</h3>
                <p className="text-sm text-gray-600">{comp.mode}</p>
                <p className="text-sm text-gray-500">
                  {comp.participant_count} participants
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Upcoming competitions */}
      {upcomingCompetitions.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-4">Upcoming Competitions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcomingCompetitions.map((comp: any) => (
              <Link
                key={comp.id}
                to={`/competitions/${comp.id}`}
                className="card hover:shadow-lg transition"
              >
                <h3 className="font-semibold">{comp.name}</h3>
                <p className="text-sm text-gray-600">{comp.mode}</p>
                <p className="text-sm text-gray-500">
                  {comp.participant_count} participants
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

**TanStack Query integration:**
- **queryKey:** Uniquely identifies this query for caching
- **queryFn:** Function that fetches data
- **Automatic caching:** Second visit to dashboard = instant (cached)
- **Auto-refetch:** Refetches on mount if data is stale (5min)

##### `pages/CompetitionDetail.tsx` - Competition View

```tsx
export default function CompetitionDetail() {
  const { id } = useParams()

  // Fetch competition details
  const { data: competition, isLoading: compLoading } = useQuery({
    queryKey: ['competition', id],
    queryFn: async () => {
      const response = await api.get(`/competitions/${id}`)
      return response.data
    }
  })

  // Fetch leaderboard (only if participant)
  const { data: leaderboard, isLoading: leaderboardLoading } = useQuery({
    queryKey: ['leaderboard', id],
    queryFn: async () => {
      const response = await api.get(`/leaderboards/${id}`)
      return response.data
    },
    enabled: !!competition?.user_is_participant  // Conditional query
  })

  if (compLoading) return <div>Loading...</div>
  if (!competition) return <div>Competition not found</div>

  return (
    <div className="space-y-6">
      {/* Competition header */}
      <div className="card">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-3xl font-bold">{competition.name}</h1>
            <p className="text-gray-600">{competition.description}</p>
          </div>
          <span className="badge badge-in-progress">
            {competition.status}
          </span>
        </div>

        {/* Metadata grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-gray-600">Mode</p>
            <p className="font-semibold">{competition.mode}</p>
          </div>
          <div>
            <p className="text-gray-600">Participants</p>
            <p className="font-semibold">{competition.participant_count}</p>
          </div>
          {/* More metadata... */}
        </div>
      </div>

      {competition.user_is_participant ? (
        <>
          {/* Leaderboard */}
          <div className="card">
            <h2 className="text-2xl font-bold mb-4">Leaderboard</h2>
            {leaderboardLoading ? (
              <p>Loading...</p>
            ) : (
              <table className="w-full">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Username</th>
                    <th>Points</th>
                    <th>Wins</th>
                    <th>Accuracy</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((entry: any) => (
                    <tr
                      key={entry.user_id}
                      className={entry.is_current_user ? 'bg-primary-50' : ''}
                    >
                      <td>{entry.rank}</td>
                      <td>
                        {entry.username}
                        {entry.is_current_user && ' (You)'}
                      </td>
                      <td>{entry.total_points}</td>
                      <td>{entry.total_wins}</td>
                      <td>{entry.accuracy_percentage.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Pick submission section (TODO) */}
          {competition.mode === 'daily_picks' && (
            <div className="card">
              <h2 className="text-2xl font-bold mb-4">Daily Picks</h2>
              <p className="text-gray-600">
                TODO: Game list with pick submission interface
              </p>
            </div>
          )}

          {competition.mode === 'fixed_teams' && (
            <div className="card">
              <h2 className="text-2xl font-bold mb-4">Fixed Team Selection</h2>
              <p className="text-gray-600">
                TODO: Team/golfer selection interface
              </p>
            </div>
          )}
        </>
      ) : (
        // Join button for non-participants
        <div className="card text-center py-8">
          <p className="mb-4">Join this competition to start competing!</p>
          <button className="btn btn-primary">
            {competition.join_type === 'open' ? 'Join Now' : 'Request to Join'}
          </button>
        </div>
      )}
    </div>
  )
}
```

**Conditional queries:**
- **enabled:** Only runs if condition is true
- **Use case:** Don't fetch leaderboard if user isn't a participant (would 403)
- **Auto-refetch:** When enabled changes from false→true, query runs

**Missing functionality:**
- Pick submission form (daily picks)
- Team/golfer selection (fixed teams)
- Join competition button handler
- Game schedule display

---

## 📍 Important Files Map

### Critical Path Files (Must Understand)

#### Backend Foundation (5 files)
1. **`backend/app/main.py`** - Application bootstrap
   - Why: Registers all routers, starts background jobs, configures CORS
   - Dependencies: All API routers, background jobs module

2. **`backend/app/core/config.py`** - Configuration brain
   - Why: Single source of truth for all settings
   - Used by: Every module that needs config

3. **`backend/app/core/security.py`** - Auth engine
   - Why: JWT creation/verification, password hashing
   - Used by: Auth API, all protected endpoints

4. **`backend/app/core/deps.py`** - Dependency injection
   - Why: Provides DB sessions and auth dependencies
   - Used by: Every API endpoint

5. **`backend/app/db/session.py`** - Database connection
   - Why: Async SQLAlchemy engine and session factory
   - Used by: All database operations

#### Core Business Logic (3 files)
6. **`backend/app/models/user.py`** - User model
   - Why: Authentication entity, roles, account status
   - Relationships: Everything links back to users

7. **`backend/app/models/competition.py`** - Competition model
   - Why: Central orchestration entity
   - Relationships: Games, picks, participants

8. **`backend/app/models/pick.py`** - Pick models
   - Why: Core prediction entities (daily + fixed)
   - Why important: Where points are scored

#### API Endpoints (2 files)
9. **`backend/app/api/picks.py`** - Pick submission
   - Why: Main user interaction (making predictions)
   - Validation: Extensive checks before accepting picks

10. **`backend/app/api/leaderboards.py`** - Rankings
    - Why: Users check standings constantly
    - Performance critical: Needs optimization

#### External Integration (2 files)
11. **`backend/app/services/sports_api/sports_service.py`** - API orchestrator
    - Why: Fetches game data from external providers
    - Critical: App doesn't work without this

12. **`backend/app/services/circuit_breaker.py`** - Fault tolerance
    - Why: Prevents cascading failures
    - Pattern: Industry-standard resilience

#### Background Processing (1 file)
13. **`backend/app/services/background_jobs.py`** - Scheduled tasks
    - Why: Automates scoring, locking, transitions
    - Status: 🔴 Not implemented yet

### Frontend Essential (4 files)
14. **`frontend/src/App.tsx`** - Router
    - Why: Defines all routes and auth guards
    - Pattern: Protected routes with redirects

15. **`frontend/src/services/authStore.ts`** - Auth state
    - Why: Global authentication state
    - Used by: Every protected component

16. **`frontend/src/services/api.ts`** - HTTP client
    - Why: Axios with JWT interceptors
    - Used by: All API calls

17. **`frontend/src/pages/CompetitionDetail.tsx`** - Main UX
    - Why: Where users spend most time (picks, leaderboard)
    - Status: ⚠️ Layout complete, pick submission TODO

---

## 🚨 Known Issues and Technical Debt

### Critical Issues (P0 - Blocking)

#### 1. 🔴 Background Jobs Not Implemented
- **Files:** `backend/app/services/background_jobs.py`
- **Lines:** 13-65 (all stubs)
- **Impact:** Core functionality doesn't work:
  - Picks never lock
  - Scores never update
  - Competitions never transition
  - Accounts never delete
- **Estimated effort:** 2-3 weeks
- **Dependencies:** Sports API clients must be implemented first

#### 2. 🔴 API Clients Are Stubs
- **Files:** `espn_client.py`, `theodds_client.py`, `rapidapi_client.py`
- **Impact:** Can't fetch game schedules or scores
- **Estimated effort:** 1-2 weeks per client
- **Recommendation:** Implement The Odds API first (has free tier)

#### 3. 🔴 No Database Migrations
- **Location:** `/backend/alembic/versions/` is empty
- **Impact:** Can't create database schema
- **Fix:** `cd backend && alembic revision --autogenerate -m "initial schema"`
- **Estimated effort:** 1 day (plus testing)

### High Priority Issues (P1 - Should Fix)

#### 4. ⚠️ league_admin_ids as ARRAY
- **File:** `backend/app/models/competition.py:67`
- **Problem:** Violates first normal form
- **Impact:** Can't query "competitions where user is admin" efficiently
- **Fix:** Create `CompetitionAdmin` junction table
- **Estimated effort:** 1 day (migration + code changes)

#### 5. ⚠️ No Pagination
- **Files:** All list endpoints
- **Impact:** Memory exhaustion with large datasets
- **Fix:** Add `limit`/`offset` parameters, default limit=50
- **Estimated effort:** 1 day

#### 6. ⚠️ Leaderboard Rank in Python
- **File:** `backend/app/api/leaderboards.py:57-71`
- **Problem:** Inefficient, doesn't handle ties
- **Fix:** Use SQL `ROW_NUMBER()` window function
- **Estimated effort:** 2 hours

#### 7. ⚠️ No Composite Indexes
- **Impact:** Slow queries on common patterns
- **Fix:** Add indexes on:
  - `Pick(user_id, competition_id)`
  - `Game(competition_id, status)`
  - `Participant(competition_id, total_points DESC)`
- **Estimated effort:** 1 hour (migration generation)

#### 8. ⚠️ Admin Check Duplication
- **Files:** `backend/app/api/admin.py` (multiple functions)
- **Problem:** Copy-pasted authorization logic
- **Fix:** Create `get_competition_admin()` dependency
- **Estimated effort:** 2 hours

#### 9. ⚠️ Global Singleton Pattern
- **File:** `backend/app/services/sports_api/sports_service.py:378`
- **Problem:** Can't mock in tests
- **Fix:** Use dependency injection
- **Estimated effort:** 4 hours

#### 10. ⚠️ No Token Refresh Logic
- **Files:** Frontend auth store, backend auth API
- **Impact:** Users logged out after 30 minutes
- **Fix:** Implement refresh token endpoint and silent refresh
- **Estimated effort:** 1 day

---

## 💡 Potential Improvements

### High Impact Improvements

#### 1. Service Layer Extraction
**Current:** Business logic in API handlers
**Proposed:** Dedicated service classes

```python
# New: backend/app/services/competition_service.py
class CompetitionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_competition(
        self,
        data: CompetitionCreate,
        creator: User
    ) -> Competition:
        """
        Encapsulates competition creation logic.

        Benefits:
        - Testable without FastAPI
        - Reusable (e.g., from CLI, admin panel)
        - Clear separation of concerns
        """
        # Validate dates
        if data.end_date <= data.start_date:
            raise ValidationError("End date must be after start date")

        # Create competition
        competition = Competition(**data.dict(), creator_id=creator.id)
        self.db.add(competition)

        # Auto-add creator as participant
        participant = Participant(
            user_id=creator.id,
            competition_id=competition.id
        )
        self.db.add(participant)

        await self.db.commit()
        return competition

# Usage in API:
@router.post("")
async def create_competition_endpoint(
    data: CompetitionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = CompetitionService(db)
    competition = await service.create_competition(data, current_user)
    return CompetitionResponse.from_orm(competition)
```

**Benefits:**
- Easier testing (no HTTP layer)
- Reusable across API/CLI/tasks
- Clear business logic separation

**Estimated effort:** 1 week

---

#### 2. Domain Events System
**Current:** Tight coupling between modules
**Proposed:** Event-driven architecture

```python
# New: backend/app/core/events.py
from typing import Callable, Dict, List
from dataclasses import dataclass

@dataclass
class DomainEvent:
    event_type: str
    payload: dict
    timestamp: datetime

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent):
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                await handler(event)

event_bus = EventBus()

# Usage:
# Subscribe to events
event_bus.subscribe("pick.locked", send_pick_locked_notification)
event_bus.subscribe("pick.locked", invalidate_user_cache)

# Publish events
await event_bus.publish(DomainEvent(
    event_type="pick.locked",
    payload={"pick_id": pick.id, "user_id": user.id}
))
```

**Use cases:**
- Notifications (email, push, in-app)
- Cache invalidation
- Analytics tracking
- Webhooks
- Audit logging

**Benefits:**
- Decoupled modules
- Easy to add features without touching core code
- Testable (mock event bus)

**Estimated effort:** 2 days

---

#### 3. Repository Pattern
**Current:** Raw SQLAlchemy queries in endpoints/services
**Proposed:** Repository abstraction

```python
# New: backend/app/repositories/competition_repository.py
class CompetitionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, competition_id: str) -> Competition | None:
        return await self.db.get(Competition, competition_id)

    async def list_active(self, user_id: str) -> List[Competition]:
        query = (
            select(Competition)
            .where(Competition.status == CompetitionStatus.ACTIVE)
            .where(Competition.id.in_(
                select(Participant.competition_id)
                .where(Participant.user_id == user_id)
            ))
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def save(self, competition: Competition):
        self.db.add(competition)
        await self.db.commit()
        await self.db.refresh(competition)
        return competition

    async def count_participants(self, competition_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Participant)
            .where(Participant.competition_id == competition_id)
        )
        return result.scalar()
```

**Benefits:**
- Encapsulates query logic
- Easy to mock in tests
- Swap database implementation (e.g., add MongoDB)
- Clear data access patterns

**Estimated effort:** 3-4 days

---

#### 4. React Error Boundaries
**Current:** Errors crash entire app
**Proposed:** Graceful error handling

```tsx
// New: frontend/src/components/ErrorBoundary.tsx
import React, { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught:', error, errorInfo)
    // TODO: Send to error tracking service (Sentry, Rollbar)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>
            Reload Page
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

// Usage in App.tsx:
<ErrorBoundary>
  <Routes>
    {/* ... */}
  </Routes>
</ErrorBoundary>
```

**Benefits:**
- Graceful degradation
- User can recover without full reload
- Track errors in production
- Better UX

**Estimated effort:** 4 hours

---

#### 5. TypeScript Interfaces
**Current:** `any` types everywhere
**Proposed:** Proper type definitions

```typescript
// New: frontend/src/types/index.ts
export interface User {
  id: string
  email: string
  username: string
  role: 'user' | 'league_admin' | 'global_admin'
  status: 'active' | 'pending_deletion' | 'deleted'
  created_at: string
  last_login_at: string | null
  has_dismissed_onboarding: boolean
}

export interface Competition {
  id: string
  name: string
  description: string | null
  mode: 'daily_picks' | 'fixed_teams'
  status: 'upcoming' | 'active' | 'completed'
  league_id: string
  start_date: string
  end_date: string
  display_timezone: string
  visibility: 'public' | 'private'
  join_type: 'open' | 'requires_approval'
  max_participants: number | null
  participant_count: number
  user_is_participant: boolean
  user_is_admin: boolean
}

export interface Pick {
  id: string
  user_id: string
  competition_id: string
  game_id: string
  predicted_winner_team_id: string
  is_locked: boolean
  locked_at: string | null
  is_correct: boolean | null
  points_earned: number
  created_at: string
  updated_at: string
}

export interface LeaderboardEntry {
  rank: number
  user_id: string
  username: string
  total_points: number
  total_wins: number
  total_losses: number
  accuracy_percentage: number
  current_streak: number
  is_current_user: boolean
}

// Usage:
const { data: competitions } = useQuery<Competition[]>({
  queryKey: ['competitions'],
  queryFn: async () => {
    const response = await api.get<Competition[]>('/competitions')
    return response.data
  }
})

// TypeScript now knows competitions is Competition[]
// Auto-complete works, catches errors at compile time
```

**Benefits:**
- Catch bugs at compile time
- IDE auto-complete
- Self-documenting code
- Refactoring confidence

**Estimated effort:** 1 day

---

## 🗺️ Development Roadmap

### Phase 1: Core Functionality (3-4 weeks)

**Week 1: Database and Basic Jobs**
- [ ] Generate database migrations
- [ ] Implement `lock_expired_picks()` job
- [ ] Implement `update_competition_statuses()` job
- [ ] Test with manual database entries

**Week 2: Sports API Integration**
- [ ] Implement The Odds API client (free tier)
- [ ] Test schedule fetching
- [ ] Test live score fetching
- [ ] Implement `update_game_scores()` job (simplified)

**Week 3: Pick Submission UI**
- [ ] Build game list component
- [ ] Build pick submission form
- [ ] Implement daily picks workflow
- [ ] Add loading and error states

**Week 4: Testing and Polish**
- [ ] End-to-end testing (register → create competition → make picks → view leaderboard)
- [ ] Fix bugs found in testing
- [ ] Add basic error handling
- [ ] Deploy to Railway for staging

### Phase 2: Production Hardening (2-3 weeks)

**Week 5: Performance and Scale**
- [ ] Add pagination to all list endpoints
- [ ] Create `CompetitionAdmin` junction table
- [ ] Add composite indexes
- [ ] Optimize leaderboard query (SQL rank)
- [ ] Add database query logging

**Week 6: Architecture Improvements**
- [ ] Extract admin authorization dependency
- [ ] Add TypeScript interfaces
- [ ] Add React Error Boundaries
- [ ] Implement token refresh logic
- [ ] Fix hard-coded redirects

**Week 7: Fixed Teams Mode**
- [ ] Implement team/golfer selection UI
- [ ] Add exclusivity validation
- [ ] Test pre-season workflow
- [ ] Test point accumulation

### Phase 3: Polish and Launch (2-3 weeks)

**Week 8: Testing**
- [ ] Unit tests for critical functions
- [ ] Integration tests for API endpoints
- [ ] E2E tests with Playwright
- [ ] Load testing with Locust

**Week 9: Monitoring and Operations**
- [ ] Add error tracking (Sentry)
- [ ] Add performance monitoring
- [ ] Set up alerts (API down, jobs failing)
- [ ] Create runbook for common issues

**Week 10: Launch Preparation**
- [ ] Security audit
- [ ] Performance audit
- [ ] Documentation review
- [ ] Staging environment testing
- [ ] Production deployment
- [ ] Monitor for issues

---

**Document Status:** Living document, update after major architectural changes
**Review Frequency:** Monthly or after significant changes
**Maintained By:** Development Team
**Last Major Revision:** 2025-01-11 (CODE_MAP.md integration)
