# 🗺️ United Degenerates League - Code Map

**Version:** 1.0.0
**Last Updated:** 2025-01-11
**Purpose:** Complete catalog of all files with descriptions, dependencies, and data shapes

---

## 📑 Table of Contents

- [Backend Structure](#backend-structure)
  - [Entry Points](#entry-points)
  - [Core Layer](#core-layer)
  - [Data Layer](#data-layer)
  - [API Layer](#api-layer)
  - [Service Layer](#service-layer)
  - [Schema Layer](#schema-layer)
- [Frontend Structure](#frontend-structure)
  - [Entry Points](#frontend-entry-points)
  - [Pages](#pages)
  - [Components](#components)
  - [Services](#services)
- [Configuration Files](#configuration-files)
- [Data Models Reference](#data-models-reference)
- [Request/Response Shapes](#requestresponse-shapes)

---

## 🔧 Backend Structure

### Entry Points

#### `backend/app/main.py`
**Purpose:** FastAPI application factory and router registration
**Lines:** 64
**Status:** ✅ Complete

**Description:**
Main application entry point. Creates FastAPI app, configures CORS, registers all API routers, and manages application lifecycle (startup/shutdown).

**Internal Dependencies:**
- `app.core.config.settings` - Application settings
- `app.api.*` - All API routers (auth, users, competitions, picks, leaderboards, admin, health)
- `app.services.background_jobs` - Scheduler lifecycle

**External Dependencies:**
- `fastapi` - Web framework
- `fastapi.middleware.cors` - CORS middleware

**Key Functions:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages startup/shutdown of background jobs"""

app = FastAPI(
    title="United Degenerates League API",
    version="1.0.0",
    lifespan=lifespan
)
```

---

### Core Layer

#### `backend/app/core/config.py`
**Purpose:** Centralized configuration management
**Lines:** 86
**Status:** ✅ Complete

**Description:**
Pydantic Settings class that loads configuration from environment variables. Manages all application settings including database, Redis, security, API keys, and caching parameters.

**Internal Dependencies:** None

**External Dependencies:**
- `pydantic-settings` - Settings management
- `typing.List` - Type hints

**Configuration Structure:**
```python
class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str]

    # Sports APIs (Multi-provider)
    ESPN_API_KEY: str
    THE_ODDS_API_KEY: str
    RAPIDAPI_KEY: str
    SPORTSDATA_API_KEY: str
    MLB_STATS_API_URL: str
    NHL_STATS_API_URL: str
    PGA_TOUR_API_KEY: str

    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT_SECONDS: int = 60

    # Caching TTLs
    CACHE_SCORES_SECONDS: int = 60
    CACHE_LEADERBOARD_SECONDS: int = 30
    CACHE_SCHEDULE_SECONDS: int = 3600

    # Background Jobs
    SCORE_UPDATE_INTERVAL_SECONDS: int = 60
```

---

#### `backend/app/core/security.py`
**Purpose:** Authentication and cryptography functions
**Lines:** 54
**Status:** ✅ Complete

**Description:**
JWT token generation/verification and password hashing using bcrypt. Handles both access tokens (30min) and refresh tokens (7 days).

**Internal Dependencies:**
- `app.core.config.settings` - Secret key and algorithm

**External Dependencies:**
- `jose.jwt` - JWT encoding/decoding
- `passlib.context.CryptContext` - Password hashing

**Key Functions:**
```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with 30min expiration"""

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token with 7-day expiration"""

def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify JWT token and return payload"""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash"""

def get_password_hash(password: str) -> str:
    """Hash password with bcrypt"""
```

**Token Structure:**
```python
{
    "sub": "user-uuid",      # Subject (user ID)
    "exp": 1234567890,       # Expiration timestamp
    "type": "access"         # Token type (access|refresh)
}
```

---

#### `backend/app/core/deps.py`
**Purpose:** FastAPI dependency injection functions
**Lines:** 92
**Status:** ✅ Complete

**Description:**
Provides reusable dependencies for database sessions, authentication, and authorization. Used via FastAPI's `Depends()` mechanism.

**Internal Dependencies:**
- `app.db.session.AsyncSessionLocal` - DB session factory
- `app.models.user.User, UserRole` - User model and roles
- `app.core.security.verify_token` - JWT verification

**External Dependencies:**
- `fastapi` - Depends, HTTPException, status codes
- `fastapi.security.HTTPBearer` - JWT bearer auth
- `sqlalchemy.ext.asyncio.AsyncSession` - Async DB session

**Key Dependencies:**
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides database session, auto-closes on exit"""

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extracts and validates JWT, returns User object"""

async def get_current_global_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Requires global admin role, raises 403 if not admin"""

async def get_optional_user(...) -> Optional[User]:
    """Returns user if authenticated, None otherwise"""
```

---

### Data Layer

#### `backend/app/db/session.py`
**Purpose:** SQLAlchemy async engine and session management
**Lines:** 29
**Status:** ✅ Complete

**Description:**
Creates async SQLAlchemy engine and session factory. Converts PostgreSQL URL to AsyncPG format.

**Internal Dependencies:**
- `app.core.config.settings` - DATABASE_URL

**External Dependencies:**
- `sqlalchemy.ext.asyncio` - AsyncSession, create_async_engine, async_sessionmaker
- `sqlalchemy.orm.declarative_base` - ORM base class

**Key Objects:**
```python
engine = create_async_engine(
    database_url,  # postgresql+asyncpg://...
    echo=True if development else False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # Don't expire objects after commit
)

Base = declarative_base()  # ORM base for all models
```

---

#### `backend/app/models/user.py`
**Purpose:** User account model
**Lines:** 50
**Status:** ✅ Complete

**Description:**
User authentication and profile model with role-based access control.

**Internal Dependencies:**
- `app.db.session.Base` - SQLAlchemy base

**External Dependencies:**
- `sqlalchemy` - Column types, relationships
- `datetime`, `uuid`, `enum` - Standard library

**Model Structure:**
```python
class UserRole(enum.Enum):
    USER = "user"
    LEAGUE_ADMIN = "league_admin"
    GLOBAL_ADMIN = "global_admin"

class AccountStatus(enum.Enum):
    ACTIVE = "active"
    PENDING_DELETION = "pending_deletion"
    DELETED = "deleted"

class User(Base):
    __tablename__ = "users"

    id: UUID (primary key)
    email: str (unique, indexed)
    username: str (unique, indexed)
    hashed_password: str
    role: UserRole
    status: AccountStatus
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime (nullable)
    deletion_requested_at: datetime (nullable)
    has_dismissed_onboarding: bool

    # Relationships
    participants: List[Participant]
    picks: List[Pick]
    fixed_team_selections: List[FixedTeamSelection]
    created_competitions: List[Competition]
    join_requests: List[JoinRequest]
```

---

#### `backend/app/models/competition.py`
**Purpose:** Competition orchestration model
**Lines:** 84
**Status:** ⚠️ Complete (ARRAY field needs refactoring)

**Description:**
Main competition entity supporting both daily picks and fixed teams modes.

**Internal Dependencies:**
- `app.db.session.Base`

**Enums:**
```python
class CompetitionMode(enum.Enum):
    DAILY_PICKS = "daily_picks"
    FIXED_TEAMS = "fixed_teams"

class CompetitionStatus(enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"

class Visibility(enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class JoinType(enum.Enum):
    OPEN = "open"
    REQUIRES_APPROVAL = "requires_approval"
```

**Model Structure:**
```python
class Competition(Base):
    __tablename__ = "competitions"

    id: UUID (primary key)
    name: str
    description: str (nullable)
    mode: CompetitionMode
    status: CompetitionStatus (indexed)
    league_id: UUID (foreign key → leagues)

    # Dates
    start_date: datetime (indexed)
    end_date: datetime (indexed)
    display_timezone: str (default "UTC")

    # Access control
    visibility: Visibility
    join_type: JoinType
    max_participants: int (nullable)

    # Mode-specific settings
    max_picks_per_day: int (nullable, for daily_picks)
    max_teams_per_participant: int (nullable, for fixed_teams)
    max_golfers_per_participant: int (nullable, for PGA)

    # Admins
    creator_id: UUID (foreign key → users)
    league_admin_ids: Array[UUID] (⚠️ Should be junction table)
    winner_user_id: UUID (nullable, for tie-breaker)

    # Relationships
    league: League
    creator: User
    participants: List[Participant]
    games: List[Game]
    picks: List[Pick]
    fixed_team_selections: List[FixedTeamSelection]
    join_requests: List[JoinRequest]
```

---

#### `backend/app/models/league.py`
**Purpose:** Sport league and team/golfer entities
**Lines:** 96
**Status:** ✅ Complete

**Description:**
Defines sports leagues (NFL, NBA, etc.) and their teams/golfers.

**Enums:**
```python
class LeagueName(enum.Enum):
    NFL = "NFL"
    NBA = "NBA"
    MLB = "MLB"
    NHL = "NHL"
    NCAA_BASKETBALL = "NCAA_BASKETBALL"
    NCAA_FOOTBALL = "NCAA_FOOTBALL"
    PGA = "PGA"
    MLS = "MLS"  # v2
    EPL = "EPL"  # v2
    UCL = "UCL"  # v2
```

**Models:**
```python
class League(Base):
    id: UUID
    name: LeagueName (unique, indexed)
    display_name: str
    is_team_based: bool

class Team(Base):
    id: UUID
    league_id: UUID
    external_id: str (indexed, from API)
    name: str
    abbreviation: str
    city: str (nullable)
    logo_url: str (nullable)
    primary_color: str (nullable)
    is_active: bool

class Golfer(Base):
    id: UUID
    league_id: UUID
    external_id: str (indexed, from PGA API)
    first_name: str
    last_name: str
    full_name: str (indexed)
    photo_url: str (nullable)
    is_active: bool
```

---

#### `backend/app/models/game.py`
**Purpose:** Individual game/match entity
**Lines:** 67
**Status:** ✅ Complete

**Description:**
Represents a single game with scores, status, and timing.

**Enums:**
```python
class GameStatus(enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINAL = "final"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    NO_RESULT = "no_result"
```

**Model Structure:**
```python
class Game(Base):
    __tablename__ = "games"

    id: UUID
    competition_id: UUID (indexed)
    external_id: str (indexed, from API)

    # Teams
    home_team_id: UUID (indexed)
    away_team_id: UUID (indexed)

    # Timing (UTC)
    scheduled_start_time: datetime (indexed)
    actual_start_time: datetime (nullable)
    end_time: datetime (nullable)

    # Status and scores
    status: GameStatus (indexed)
    home_team_score: int (nullable)
    away_team_score: int (nullable)
    winner_team_id: UUID (nullable, indexed)

    # Venue
    venue_name: str (nullable)
    venue_city: str (nullable)

    # Raw API data
    api_data: JSON (nullable)

    # Score corrections
    score_corrected_at: datetime (nullable)
    score_correction_count: int (default 0, max 1 per spec)

    # Relationships
    competition: Competition
    home_team: Team
    away_team: Team
    picks: List[Pick]
```

---

#### `backend/app/models/pick.py`
**Purpose:** Pick entities (daily and fixed)
**Lines:** 82
**Status:** ✅ Complete

**Description:**
Two types of picks: daily predictions for individual games, and fixed team/golfer selections for entire season.

**Models:**
```python
class Pick(Base):
    """Daily Picks - per-game predictions"""
    __tablename__ = "picks"

    id: UUID
    user_id: UUID (indexed)
    competition_id: UUID (indexed)
    game_id: UUID (indexed)
    predicted_winner_team_id: UUID

    # Locking
    is_locked: bool (indexed)
    locked_at: datetime (nullable)

    # Scoring
    is_correct: bool (nullable, set after game finishes)
    points_earned: int (default 0)

    # Constraint: One pick per user per game per competition

class FixedTeamSelection(Base):
    """Fixed Teams - pre-season selections"""
    __tablename__ = "fixed_team_selections"

    id: UUID
    user_id: UUID (indexed)
    competition_id: UUID (indexed)

    # XOR: Either team OR golfer, not both
    team_id: UUID (nullable, indexed)
    golfer_id: UUID (nullable, indexed)

    # Locking
    is_locked: bool (indexed)
    locked_at: datetime (nullable)

    # Scoring (accumulated over season)
    total_points: int (default 0)

    # Constraint: Must have team_id XOR golfer_id
```

---

#### `backend/app/models/participant.py`
**Purpose:** User participation and join requests
**Lines:** 70
**Status:** ✅ Complete

**Description:**
Links users to competitions with scoring stats, plus join request workflow.

**Enums:**
```python
class JoinRequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
```

**Models:**
```python
class Participant(Base):
    """User's participation in a competition"""
    __tablename__ = "participants"

    id: UUID
    user_id: UUID (indexed)
    competition_id: UUID (indexed)

    # Scoring aggregates
    total_points: int (default 0, indexed)
    total_wins: int (default 0)
    total_losses: int (default 0)
    accuracy_percentage: float (default 0.0)
    current_streak: int (default 0)

    # Timestamps
    joined_at: datetime
    last_pick_at: datetime (nullable)

class JoinRequest(Base):
    """Join request for private competitions"""
    __tablename__ = "join_requests"

    id: UUID
    user_id: UUID (indexed)
    competition_id: UUID (indexed)
    status: JoinRequestStatus (indexed)

    # Review
    reviewed_by_user_id: UUID (nullable)
    reviewed_at: datetime (nullable)
    rejection_reason: str (nullable)
```

---

#### `backend/app/models/audit_log.py`
**Purpose:** Immutable audit trail
**Lines:** 59
**Status:** ✅ Complete

**Description:**
Logs all admin actions for compliance and debugging. Append-only, no updates or deletes.

**Enums:**
```python
class AuditAction(enum.Enum):
    COMPETITION_CREATED = "competition_created"
    COMPETITION_DELETED = "competition_deleted"
    COMPETITION_STATUS_CHANGED = "competition_status_changed"
    COMPETITION_SETTINGS_CHANGED = "competition_settings_changed"
    USER_DELETED = "user_deleted"
    USER_ROLE_CHANGED = "user_role_changed"
    ADMIN_ADDED = "admin_added"
    ADMIN_REMOVED = "admin_removed"
    SCORE_CORRECTED = "score_corrected"
    WINNER_DESIGNATED = "winner_designated"
    JOIN_REQUEST_APPROVED = "join_request_approved"
    JOIN_REQUEST_REJECTED = "join_request_rejected"
```

**Model Structure:**
```python
class AuditLog(Base):
    """Immutable audit log"""
    __tablename__ = "audit_logs"

    id: UUID
    admin_user_id: UUID (indexed)
    action: AuditAction (indexed)
    target_type: str (e.g., "competition", "user")
    target_id: UUID (nullable, indexed)
    details: JSON (nullable, additional context)
    created_at: datetime (indexed)

    # No relationships - immutable records
```

---

### API Layer

#### `backend/app/api/auth.py`
**Purpose:** Authentication endpoints
**Lines:** 101
**Status:** ✅ Complete

**Description:**
User registration and login with JWT token issuance.

**Internal Dependencies:**
- `app.core.deps.get_db`
- `app.core.security.*` - Password and token functions
- `app.models.user.User, AccountStatus`
- `app.schemas.user.*` - Request/response schemas

**Endpoints:**
```python
POST /api/auth/register
    Request: UserCreate {email, username, password}
    Response: TokenResponse {access_token, refresh_token, user}
    Status: 201 Created

POST /api/auth/login
    Request: UserLogin {email, password}
    Response: TokenResponse {access_token, refresh_token, user}
    Status: 200 OK

Error Cases:
    - 400: Email already registered / username taken
    - 401: Incorrect credentials
    - 403: Account not active
```

---

#### `backend/app/api/users.py`
**Purpose:** User profile management
**Lines:** 101
**Status:** ✅ Complete

**Description:**
User profile operations, password changes, account deletion.

**Internal Dependencies:**
- `app.core.deps.get_db, get_current_user`
- `app.models.user.User, AccountStatus`
- `app.schemas.user.*`

**Endpoints:**
```python
GET /api/users/me
    Response: UserResponse
    Auth: Required

PATCH /api/users/me
    Request: UserUpdate {username?, has_dismissed_onboarding?}
    Response: UserResponse
    Auth: Required

POST /api/users/me/change-password
    Request: PasswordChange {current_password, new_password}
    Response: {message: "Password updated successfully"}
    Auth: Required
    Errors: 400 if current password incorrect

DELETE /api/users/me
    Request: None
    Response: {message, deletion_date, grace_period_days: 30}
    Auth: Required
    Note: Sets status to PENDING_DELETION

POST /api/users/me/cancel-deletion
    Response: {message: "Account deletion cancelled"}
    Auth: Required
    Errors: 400 if no pending deletion
```

---

#### `backend/app/api/competitions.py`
**Purpose:** Competition CRUD and join operations
**Lines:** 200+ (estimated)
**Status:** ✅ Complete

**Description:**
Create, list, update, delete competitions. Handle join requests.

**Internal Dependencies:**
- `app.core.deps.get_db, get_current_user, get_current_global_admin`
- `app.models.competition.*, participant.*`
- `app.schemas.competition.*`

**Endpoints:**
```python
POST /api/competitions
    Request: CompetitionCreate
    Response: CompetitionResponse (status 201)
    Auth: Required
    Note: Auto-adds creator as participant and admin

GET /api/competitions
    Query: status_filter?, visibility?
    Response: List[CompetitionListResponse]
    Auth: Required
    Logic: Shows public + user's private competitions

GET /api/competitions/{id}
    Response: CompetitionResponse
    Auth: Required
    Includes: participant_count, user_is_participant, user_is_admin

PATCH /api/competitions/{id}
    Request: CompetitionUpdate
    Response: CompetitionResponse
    Auth: Admin only
    Errors: 403 if not admin

DELETE /api/competitions/{id}
    Auth: Global admin only
    Errors: 403 if not global admin

POST /api/competitions/{id}/join
    Response: {message: "Joined competition" | "Join request created"}
    Auth: Required
    Logic: Instant join if OPEN, creates JoinRequest if REQUIRES_APPROVAL
    Errors: 400 if already joined, 400 if max participants reached
```

---

#### `backend/app/api/picks.py`
**Purpose:** Pick submission (daily and fixed)
**Lines:** 200+ (estimated)
**Status:** ✅ Complete

**Description:**
Submit and manage daily picks and fixed team selections.

**Internal Dependencies:**
- `app.core.deps.get_db, get_current_user`
- `app.models.pick.*, game.*, competition.*, participant.*`
- `app.schemas.pick.*`

**Endpoints:**
```python
POST /api/picks/{competition_id}/daily
    Request: PickCreate {game_id, predicted_winner_team_id}
    Response: PickResponse (status 201)
    Auth: Required
    Validation:
        - User is participant
        - Game exists and not started
        - Daily limit not exceeded
        - Team valid for game
    Note: Updates existing pick if already exists

GET /api/picks/{competition_id}/daily
    Response: List[PickResponse]
    Auth: Required
    Returns: User's daily picks for competition

POST /api/picks/{competition_id}/fixed
    Request: FixedTeamSelectionCreate {team_id? | golfer_id?}
    Response: FixedTeamSelectionResponse (status 201)
    Auth: Required
    Validation:
        - User is participant
        - Competition in fixed_teams mode
        - Not yet locked (before start_date)
        - Max selections not exceeded
        - Team/golfer not taken (exclusivity)

GET /api/picks/{competition_id}/fixed
    Response: List[FixedTeamSelectionResponse]
    Auth: Required
```

---

#### `backend/app/api/leaderboards.py`
**Purpose:** Competition rankings
**Lines:** 74
**Status:** ✅ Complete

**Description:**
Get leaderboard with sorting options.

**Internal Dependencies:**
- `app.core.deps.get_db, get_current_user`
- `app.models.competition.*, participant.*`
- `app.schemas.participant.LeaderboardEntry`

**Endpoints:**
```python
GET /api/leaderboards/{competition_id}
    Query: sort_by? = "points" | "accuracy" | "wins" | "streak"
    Response: List[LeaderboardEntry]
    Auth: Required

    LeaderboardEntry {
        rank: int (calculated in Python, should use SQL)
        user_id: UUID
        username: str
        total_points: int
        total_wins: int
        total_losses: int
        accuracy_percentage: float
        current_streak: int
        is_current_user: bool
    }

    Errors: 404 if competition not found
```

---

#### `backend/app/api/admin.py`
**Purpose:** Admin operations
**Lines:** 240
**Status:** ✅ Complete

**Description:**
Join request approval/rejection and audit log viewing.

**Internal Dependencies:**
- `app.core.deps.get_db, get_current_user, get_current_global_admin`
- `app.models.participant.JoinRequest, competition.*, audit_log.*`
- `app.schemas.participant.JoinRequestResponse`

**Endpoints:**
```python
GET /api/admin/join-requests/{competition_id}
    Query: status_filter? = pending | approved | rejected
    Response: List[JoinRequestResponse]
    Auth: Competition admin or global admin
    Errors: 403 if not admin

POST /api/admin/join-requests/{request_id}/approve
    Response: {message: "Join request approved"}
    Auth: Competition admin or global admin
    Side Effects:
        - Creates Participant record
        - Creates AuditLog entry
    Errors: 404 if request not found, 403 if not admin

POST /api/admin/join-requests/{request_id}/reject
    Request: reason? (optional string)
    Response: {message: "Join request rejected"}
    Auth: Competition admin or global admin
    Side Effects:
        - Updates JoinRequest status
        - Creates AuditLog entry with reason

GET /api/admin/audit-logs
    Query: competition_id?, action_filter?, limit=50, offset=0
    Response: List[AuditLog JSON]
    Auth: Admin (filtered by permissions)
    Note: Global admins see all, league admins see their competitions
```

---

#### `backend/app/api/health.py`
**Purpose:** Health monitoring
**Lines:** 38
**Status:** ✅ Complete

**Description:**
API health checks and circuit breaker management.

**Internal Dependencies:**
- `app.core.deps.get_current_user, get_current_global_admin`
- `app.services.sports_api.sports_service`
- `app.services.circuit_breaker.circuit_breaker_manager`

**Endpoints:**
```python
GET /api/health/api-status
    Response: {
        configured_apis: List[str],
        circuit_breakers: Dict[str, CircuitBreakerStatus],
        cache_status: "connected" | "disconnected"
    }
    Auth: Required

POST /api/health/reset-circuit-breakers
    Response: {
        message: "All circuit breakers have been reset",
        status: Dict[str, CircuitBreakerStatus]
    }
    Auth: Global admin only
```

---

### Service Layer

#### `backend/app/services/sports_api/sports_service.py`
**Purpose:** Multi-API orchestrator with failover
**Lines:** 379
**Status:** ⚠️ Orchestrator complete, clients are stubs

**Description:**
Main service that coordinates multiple sports API providers with circuit breaker pattern, Redis caching, and automatic failover.

**Internal Dependencies:**
- `app.services.sports_api.base.*` - Base client and data structures
- `app.services.sports_api.espn_client.ESPNAPIClient`
- `app.services.sports_api.theodds_client.TheOddsAPIClient`
- `app.services.sports_api.rapidapi_client.RapidAPIClient`
- `app.services.circuit_breaker.*`
- `app.core.config.settings`

**External Dependencies:**
- `redis` - Caching layer
- `httpx` - HTTP client (in sub-clients)
- `logging` - Structured logging

**Key Methods:**
```python
class SportsDataService:
    clients: List[BaseSportsAPIClient]  # Priority order
    redis_client: Redis

    async def get_schedule(
        league: str,
        start_date: datetime,
        end_date: datetime,
        use_cache: bool = True
    ) -> List[GameData]:
        """
        Fetch game schedule with failover
        1. Check Redis cache (TTL: 3600s)
        2. Try ESPN → The Odds → RapidAPI
        3. Each client wrapped in circuit breaker
        4. Fall back to stale cache if all fail
        """

    async def get_live_scores(
        league: str,
        use_cache: bool = True
    ) -> List[GameData]:
        """
        Fetch live scores with failover
        Cache TTL: 60s (live data changes fast)
        """

    async def get_game_details(
        league: str,
        game_id: str,
        use_cache: bool = True
    ) -> Optional[GameData]:
        """Fetch single game details"""

    def get_api_health_status() -> Dict:
        """
        Returns:
            - configured_apis: List of available providers
            - circuit_breakers: Status of all breakers
            - cache_status: Redis connection state
        """
```

**GameData Structure:**
```python
class GameData:
    external_id: str
    home_team: str
    away_team: str
    scheduled_start_time: datetime
    status: str  # "scheduled" | "in_progress" | "final"
    home_score: int | None
    away_score: int | None
    venue: str | None
    raw_data: dict  # Original API response
```

---

#### `backend/app/services/sports_api/base.py`
**Purpose:** Abstract base for API clients
**Lines:** 80+
**Status:** ✅ Complete

**Description:**
Defines interface that all sports API clients must implement.

**Enums:**
```python
class APIProvider(enum.Enum):
    ESPN = "espn"
    THE_ODDS_API = "the_odds_api"
    RAPIDAPI = "rapidapi"
    SPORTSDATA = "sportsdata"
    MLB_STATS = "mlb_stats"
    NHL_STATS = "nhl_stats"
    PGA_TOUR = "pga_tour"
```

**Base Class:**
```python
class BaseSportsAPIClient(ABC):
    provider: APIProvider
    client: httpx.AsyncClient

    @abstractmethod
    async def get_schedule(
        league: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[GameData]:
        """Fetch game schedule"""

    @abstractmethod
    async def get_live_scores(league: str) -> List[GameData]:
        """Fetch live scores"""

    @abstractmethod
    async def get_game_details(
        league: str,
        game_id: str
    ) -> Optional[GameData]:
        """Fetch single game"""
```

**Custom Exceptions:**
```python
class RateLimitExceededError(Exception):
    """Raised when API rate limit hit"""

class APIUnavailableError(Exception):
    """Raised when all APIs fail"""
```

---

#### `backend/app/services/sports_api/espn_client.py`
**Purpose:** ESPN API integration
**Status:** 🔴 Stub only

**Expected Interface:**
```python
class ESPNAPIClient(BaseSportsAPIClient):
    def __init__(self):
        super().__init__(APIProvider.ESPN)
        self.api_key = settings.ESPN_API_KEY
        self.base_url = settings.ESPN_API_BASE_URL

    async def get_schedule(...) -> List[GameData]:
        # Call ESPN API
        # Parse response to GameData
        # Handle rate limits
```

---

#### `backend/app/services/sports_api/theodds_client.py`
**Purpose:** The Odds API integration
**Status:** 🔴 Stub only

**Expected Interface:**
```python
class TheOddsAPIClient(BaseSportsAPIClient):
    def __init__(self):
        super().__init__(APIProvider.THE_ODDS_API)
        self.api_key = settings.THE_ODDS_API_KEY
        self.base_url = settings.THE_ODDS_API_BASE_URL
```

---

#### `backend/app/services/sports_api/rapidapi_client.py`
**Purpose:** RapidAPI integration
**Status:** 🔴 Stub only

---

#### `backend/app/services/circuit_breaker.py`
**Purpose:** Circuit breaker pattern implementation
**Lines:** 164
**Status:** ✅ Complete

**Description:**
Prevents cascading failures by temporarily stopping requests to failing services.

**External Dependencies:**
- `datetime`, `enum` - Standard library

**Key Classes:**
```python
class CircuitState(enum.Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit tripped, rejecting
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    timeout_seconds: int = 60

    state: CircuitState
    failure_count: int
    last_failure_time: datetime | None
    last_success_time: datetime | None

    def call(func, *args, **kwargs):
        """
        Execute function with circuit breaker protection

        State Transitions:
        1. CLOSED: Normal, allows all calls
        2. After 5 failures → OPEN
        3. OPEN: Rejects all calls for 60s
        4. After 60s → HALF_OPEN
        5. HALF_OPEN: Try one call
           - Success → CLOSED
           - Failure → OPEN
        """

    def get_status() -> dict:
        """
        Returns:
            - name
            - state
            - failure_count
            - last_failure_time
            - time_until_reset
        """

class CircuitBreakerManager:
    breakers: Dict[str, CircuitBreaker]

    def get_breaker(name, threshold, timeout) -> CircuitBreaker:
        """Get or create breaker by name"""

    def reset_all():
        """Manually reset all breakers"""

    def get_all_status() -> Dict[str, dict]:
        """Status of all breakers"""
```

---

#### `backend/app/services/background_jobs.py`
**Purpose:** Scheduled background tasks
**Lines:** 119
**Status:** 🔴 All jobs are TODO stubs

**Description:**
APScheduler jobs for score updates, competition transitions, pick locking, and account cleanup.

**Internal Dependencies:**
- `app.core.config.settings`

**External Dependencies:**
- `apscheduler.schedulers.background.BackgroundScheduler`
- `apscheduler.triggers.interval.IntervalTrigger`

**Jobs:**
```python
async def update_game_scores():
    """
    Runs every 60 seconds
    TODO:
        1. Fetch active/in-progress games
        2. Call sports APIs for latest scores
        3. Update Game records
        4. Recalculate Pick.is_correct and points_earned
        5. Update Participant totals
        6. Invalidate leaderboard cache
    """

async def update_competition_statuses():
    """
    Runs every 5 minutes
    TODO:
        1. Check competitions with start_date <= now → set ACTIVE
        2. Check competitions with end_date <= now + all games FINAL → set COMPLETED
        3. Lock FixedTeamSelection when active
        4. Freeze standings when completed
    """

async def lock_expired_picks():
    """
    Runs every 60 seconds
    TODO:
        1. Find games where scheduled_start_time <= now
        2. Set Pick.is_locked = True for those games
        3. Set Pick.locked_at = now
    """

async def cleanup_pending_deletions():
    """
    Runs daily at 2 AM UTC
    TODO:
        1. Find users with status=PENDING_DELETION
        2. Check deletion_requested_at > 30 days ago
        3. Anonymize user data (set email/username to random)
        4. Set status=DELETED
    """

def start_background_jobs():
    """Initialize scheduler and add all jobs"""

def stop_background_jobs():
    """Shutdown scheduler gracefully"""
```

---

### Schema Layer

#### `backend/app/schemas/user.py`
**Purpose:** User request/response schemas
**Lines:** 48
**Status:** ✅ Complete

**Schemas:**
```python
class UserBase(BaseModel):
    email: EmailStr
    username: str (min 3, max 50)

class UserCreate(UserBase):
    password: str (min 8, max 100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: UUID4
    role: UserRole
    status: AccountStatus
    created_at: datetime
    last_login_at: datetime | None
    has_dismissed_onboarding: bool

    class Config:
        from_attributes = True  # For ORM compatibility

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserUpdate(BaseModel):
    username: str | None (min 3, max 50)
    has_dismissed_onboarding: bool | None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str (min 8, max 100)
```

---

#### `backend/app/schemas/competition.py`
**Purpose:** Competition request/response schemas
**Lines:** 71
**Status:** ✅ Complete

**Schemas:**
```python
class CompetitionBase(BaseModel):
    name: str (min 1, max 200)
    description: str | None
    mode: CompetitionMode
    league_id: UUID4
    start_date: datetime
    end_date: datetime
    display_timezone: str = "UTC"
    visibility: Visibility = PRIVATE
    join_type: JoinType = REQUIRES_APPROVAL
    max_participants: int | None
    max_picks_per_day: int | None
    max_teams_per_participant: int | None
    max_golfers_per_participant: int | None

class CompetitionCreate(CompetitionBase):
    pass

class CompetitionUpdate(BaseModel):
    # All fields optional for partial updates
    name: str | None
    description: str | None
    start_date: datetime | None
    end_date: datetime | None
    visibility: Visibility | None
    join_type: JoinType | None
    max_participants: int | None
    max_picks_per_day: int | None
    status: CompetitionStatus | None

class CompetitionResponse(CompetitionBase):
    id: UUID4
    status: CompetitionStatus
    creator_id: UUID4
    league_admin_ids: List[UUID4]
    winner_user_id: UUID4 | None
    created_at: datetime
    updated_at: datetime

    # Computed fields
    participant_count: int | None
    user_is_participant: bool | None
    user_is_admin: bool | None

class CompetitionListResponse(BaseModel):
    # Lighter version for list endpoints
    id: UUID4
    name: str
    mode: CompetitionMode
    status: CompetitionStatus
    league_id: UUID4
    start_date: datetime
    end_date: datetime
    visibility: Visibility
    participant_count: int
    max_participants: int | None
    user_is_participant: bool
```

---

#### `backend/app/schemas/pick.py`
**Purpose:** Pick request/response schemas
**Lines:** 50
**Status:** ✅ Complete

**Schemas:**
```python
class PickCreate(BaseModel):
    game_id: UUID4
    predicted_winner_team_id: UUID4

class PickUpdate(BaseModel):
    predicted_winner_team_id: UUID4

class PickResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    game_id: UUID4
    predicted_winner_team_id: UUID4
    is_locked: bool
    locked_at: datetime | None
    is_correct: bool | None  # Null until game finishes
    points_earned: int
    created_at: datetime
    updated_at: datetime

class FixedTeamSelectionCreate(BaseModel):
    team_id: UUID4 | None
    golfer_id: UUID4 | None
    # Must provide exactly one

class FixedTeamSelectionResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    team_id: UUID4 | None
    golfer_id: UUID4 | None
    is_locked: bool
    locked_at: datetime | None
    total_points: int
    created_at: datetime
```

---

#### `backend/app/schemas/participant.py`
**Purpose:** Participant and leaderboard schemas
**Lines:** 53
**Status:** ✅ Complete

**Schemas:**
```python
class ParticipantResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    total_points: int
    total_wins: int
    total_losses: int
    accuracy_percentage: float
    current_streak: int
    joined_at: datetime
    last_pick_at: datetime | None

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID4
    username: str
    total_points: int
    total_wins: int
    total_losses: int
    accuracy_percentage: float
    current_streak: int
    is_current_user: bool = False

class JoinRequestCreate(BaseModel):
    competition_id: UUID4

class JoinRequestResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    competition_id: UUID4
    status: str  # "pending" | "approved" | "rejected"
    reviewed_by_user_id: UUID4 | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
```

---

## 🎨 Frontend Structure

### Frontend Entry Points

#### `frontend/src/main.tsx`
**Purpose:** React application root
**Lines:** ~30 (estimated)
**Status:** ✅ Complete

**Description:**
Entry point that mounts React app with TanStack Query provider.

**Internal Dependencies:**
- `./App` - Main router component

**External Dependencies:**
- `react`, `react-dom` - React framework
- `react-router-dom.BrowserRouter` - Client-side routing
- `@tanstack/react-query.QueryClient, QueryClientProvider` - Server state

**Structure:**
```tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,  // 5 minutes
      refetchOnWindowFocus: false
    }
  }
})

root.render(
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </QueryClientProvider>
)
```

---

#### `frontend/src/App.tsx`
**Purpose:** Main router with auth guards
**Lines:** 28
**Status:** ✅ Complete

**Description:**
Defines all routes with authentication-based redirects.

**Internal Dependencies:**
- `./services/authStore` - Auth state
- `./pages/*` - All page components
- `./components/Layout` - Navigation wrapper

**External Dependencies:**
- `react-router-dom` - Routes, Route, Navigate

**Route Structure:**
```tsx
function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      {/* Public routes - redirect if authenticated */}
      <Route path="/login"
        element={isAuthenticated ? <Navigate to="/" /> : <Login />}
      />
      <Route path="/register"
        element={isAuthenticated ? <Navigate to="/" /> : <Register />}
      />

      {/* Protected routes - redirect if not authenticated */}
      <Route element={<Layout />}>  {/* Wrapper with nav */}
        <Route path="/"
          element={isAuthenticated ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route path="/competitions"
          element={isAuthenticated ? <Competitions /> : <Navigate to="/login" />}
        />
        <Route path="/competitions/:id"
          element={isAuthenticated ? <CompetitionDetail /> : <Navigate to="/login" />}
        />
      </Route>
    </Routes>
  )
}
```

---

### Pages

#### `frontend/src/pages/Dashboard.tsx`
**Purpose:** User home page
**Lines:** 94
**Status:** ✅ Complete

**Description:**
Shows active and upcoming competitions the user has joined.

**Internal Dependencies:**
- `../services/api` - HTTP client

**External Dependencies:**
- `@tanstack/react-query.useQuery` - Data fetching
- `react-router-dom.Link` - Navigation

**Data Flow:**
```tsx
const { data: competitions, isLoading } = useQuery({
  queryKey: ['competitions'],
  queryFn: async () => {
    const response = await api.get('/competitions')
    return response.data
  }
})

// Filters
const activeCompetitions = competitions?.filter(c => c.status === 'active')
const upcomingCompetitions = competitions?.filter(c => c.status === 'upcoming')
```

**UI Components:**
- Empty state if no competitions
- Grid of competition cards (active)
- Grid of competition cards (upcoming)
- Link to browse all competitions

---

#### `frontend/src/pages/Competitions.tsx`
**Purpose:** Browse all available competitions
**Lines:** 69
**Status:** ✅ Complete

**Description:**
Lists all competitions (public + user's private ones) with join buttons.

**Data Flow:**
```tsx
const { data: competitions, isLoading } = useQuery({
  queryKey: ['all-competitions'],
  queryFn: async () => {
    const response = await api.get('/competitions')
    return response.data
  }
})
```

**UI Components:**
- Grid of competition cards
- Status badges (active, upcoming, completed)
- Participant count
- "Join Competition" or "View Details" button

---

#### `frontend/src/pages/CompetitionDetail.tsx`
**Purpose:** Competition details and pick submission
**Lines:** 154
**Status:** ⚠️ Layout complete, pick submission TODO

**Description:**
Shows competition details, leaderboard, and pick submission interface.

**Data Flow:**
```tsx
const { id } = useParams()

const { data: competition } = useQuery({
  queryKey: ['competition', id],
  queryFn: async () => {
    const response = await api.get(`/competitions/${id}`)
    return response.data
  }
})

const { data: leaderboard } = useQuery({
  queryKey: ['leaderboard', id],
  queryFn: async () => {
    const response = await api.get(`/leaderboards/${id}`)
    return response.data
  },
  enabled: !!competition?.user_is_participant
})
```

**UI Sections:**
1. **Competition Header** - Name, description, status badge, metadata
2. **Leaderboard Table** - Rank, username, points, wins, accuracy
3. **Daily Picks Section** - TODO: Game list with prediction interface
4. **Fixed Teams Section** - TODO: Team/golfer selection interface
5. **Join Button** - If not participant

---

#### `frontend/src/pages/Login.tsx`
**Purpose:** User login form
**Lines:** ~80 (estimated)
**Status:** 🔴 Stub (basic structure only)

**Expected Structure:**
```tsx
function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { login } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {/* Email input */}
      {/* Password input */}
      {/* Error display */}
      {/* Submit button */}
      {/* Link to register */}
    </form>
  )
}
```

---

#### `frontend/src/pages/Register.tsx`
**Purpose:** User registration form
**Lines:** ~100 (estimated)
**Status:** 🔴 Stub (basic structure only)

**Expected Structure:**
```tsx
function Register() {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: ''
  })
  const [errors, setErrors] = useState({})
  const { register } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setErrors({ confirmPassword: 'Passwords do not match' })
      return
    }

    try {
      await register(formData.email, formData.username, formData.password)
      navigate('/')
    } catch (err) {
      setErrors({ submit: err.response?.data?.detail || 'Registration failed' })
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
    </form>
  )
}
```

---

### Components

#### `frontend/src/components/Layout.tsx`
**Purpose:** Navigation wrapper for authenticated routes
**Lines:** 47
**Status:** ✅ Complete

**Description:**
Provides navigation bar, footer, and outlet for child routes.

**Internal Dependencies:**
- `../services/authStore` - User and logout

**External Dependencies:**
- `react-router-dom.Outlet, Link` - Routing

**Structure:**
```tsx
function Layout() {
  const { user, logout } = useAuthStore()

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-primary-600 text-white">
        <div className="max-w-7xl mx-auto flex justify-between">
          <div className="flex space-x-8">
            <Link to="/">Dashboard</Link>
            <Link to="/competitions">Competitions</Link>
          </div>
          <div className="flex items-center space-x-4">
            <span>{user?.username}</span>
            <button onClick={logout}>Logout</button>
          </div>
        </div>
      </nav>

      <main className="flex-1 max-w-7xl w-full mx-auto py-8">
        <Outlet />  {/* Child routes render here */}
      </main>

      <footer className="bg-gray-100 py-4">
        <p>&copy; 2025 United Degenerates League</p>
      </footer>
    </div>
  )
}
```

---

### Services

#### `frontend/src/services/api.ts`
**Purpose:** Axios HTTP client with JWT interceptors
**Lines:** 35
**Status:** ✅ Complete

**Description:**
Configured Axios instance that automatically adds JWT tokens to requests and handles auth errors.

**External Dependencies:**
- `axios` - HTTP client

**Configuration:**
```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor: Add JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'  // ⚠️ Hard-coded redirect
    }
    return Promise.reject(error)
  }
)
```

---

#### `frontend/src/services/authStore.ts`
**Purpose:** Zustand auth state management
**Lines:** 64
**Status:** ✅ Complete

**Description:**
Global store for authentication state with login, register, and logout actions.

**External Dependencies:**
- `zustand` - State management
- `./api` - HTTP client

**Store Structure:**
```typescript
interface User {
  id: string
  email: string
  username: string
  role: string
  status: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),

  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password })
    const { access_token, refresh_token, user } = response.data

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
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
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, isAuthenticated: false })
    }
  }
}))
```

---

## ⚙️ Configuration Files

### Backend Configuration

#### `backend/requirements.txt`
**Purpose:** Python dependencies
**Key Packages:**
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
redis==5.0.1
httpx==0.26.0
APScheduler==3.10.4
python-dotenv==1.0.0
tenacity==8.2.3
```

#### `backend/.env`
**Purpose:** Environment variables (secrets)
**Key Variables:**
```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0

# Security
SECRET_KEY=strong-random-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Environment
ENVIRONMENT=development|production

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Sports APIs
ESPN_API_KEY=
THE_ODDS_API_KEY=
RAPIDAPI_KEY=
SPORTSDATA_API_KEY=
PGA_TOUR_API_KEY=

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60

# Caching (seconds)
CACHE_SCORES_SECONDS=60
CACHE_LEADERBOARD_SECONDS=30
CACHE_SCHEDULE_SECONDS=3600

# Background Jobs
SCORE_UPDATE_INTERVAL_SECONDS=60
```

#### `backend/alembic.ini`
**Purpose:** Alembic migration configuration
**Key Settings:**
```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://udl_user:udl_password@localhost:5432/udl_db
```

---

### Frontend Configuration

#### `frontend/package.json`
**Purpose:** Node dependencies and scripts
**Scripts:**
```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 3000",
    "build": "tsc && vite build",
    "preview": "vite preview --host 0.0.0.0 --port $PORT",
    "lint": "eslint . --ext ts,tsx"
  }
}
```

**Key Dependencies:**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "@tanstack/react-query": "^5.17.0",
    "axios": "^1.6.2",
    "date-fns": "^3.0.6",
    "zustand": "^4.4.7"
  },
  "devDependencies": {
    "typescript": "^5.2.2",
    "vite": "^5.0.8",
    "tailwindcss": "^3.3.6",
    "@vitejs/plugin-react": "^4.2.1"
  }
}
```

#### `frontend/vite.config.ts`
**Purpose:** Vite build configuration
```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000
  }
})
```

#### `frontend/tailwind.config.js`
**Purpose:** Tailwind CSS configuration
```javascript
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: { /* custom colors */ },
        secondary: { /* custom colors */ }
      }
    }
  }
}
```

---

### Deployment Configuration

#### `docker-compose.yml`
**Purpose:** Multi-container local development
**Services:**
```yaml
services:
  postgres:
    image: postgres:15-alpine
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    command: uvicorn app.main:app --reload

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
    command: npm run dev
```

#### `Dockerfile` (root)
**Purpose:** Railway.app deployment
**Multi-stage:** Python 3.11-slim base, copies entire project

#### `railway.toml` / `railway.json`
**Purpose:** Railway.app configuration
**Root Directory:** `backend/`
**Build Command:** Auto-detected
**Start Command:** Defined in `start.sh`

---

## 📊 Data Models Reference

### Complete Entity Relationship Diagram

```
┌────────────┐
│    User    │
└─────┬──────┘
      │
      ├─────────────────────┐
      │                     │
      ▼                     ▼
┌────────────┐      ┌──────────────┐
│Participant │      │  Competition │
└─────┬──────┘      └──────┬───────┘
      │                    │
      │             ┌──────┴───────┬──────────┐
      │             ▼              ▼          ▼
      │        ┌────────┐    ┌────────┐ ┌────────┐
      │        │  Game  │    │ League │ │  Join  │
      │        └────┬───┘    └────┬───┘ │Request │
      │             │             │     └────────┘
      ▼             ▼             ▼
┌────────┐    ┌─────────┐   ┌────────┐
│  Pick  │    │  Team   │   │ Golfer │
└────────┘    └─────────┘   └────────┘
      │             │             │
      └─────────────┴─────────────┘
                    │
              ┌─────▼──────┐
              │FixedTeam   │
              │ Selection  │
              └────────────┘
```

### Model Size Estimates

| Model | Avg Record Size | Expected Records | Storage Est. |
|-------|-----------------|------------------|--------------|
| User | 500 bytes | 1,000 - 10,000 | 0.5 - 5 MB |
| Competition | 800 bytes | 100 - 1,000 | 0.1 - 1 MB |
| League | 200 bytes | 10 | 2 KB |
| Team | 400 bytes | 500 | 200 KB |
| Golfer | 300 bytes | 200 | 60 KB |
| Game | 600 bytes | 10,000+ | 6+ MB |
| Pick | 300 bytes | 100,000+ | 30+ MB |
| Participant | 250 bytes | 5,000+ | 1.25+ MB |
| JoinRequest | 300 bytes | 1,000+ | 300 KB |
| AuditLog | 500 bytes | 10,000+ | 5+ MB |

**Total Estimated:** 50-100 MB for first year

---

## 🔄 Request/Response Shapes

### Authentication Endpoints

#### POST /api/auth/register
```typescript
// Request
{
  email: string
  username: string
  password: string
}

// Response 201
{
  access_token: string
  refresh_token: string
  token_type: "bearer"
  user: {
    id: string
    email: string
    username: string
    role: "user" | "league_admin" | "global_admin"
    status: "active" | "pending_deletion" | "deleted"
    created_at: string
    last_login_at: string | null
    has_dismissed_onboarding: boolean
  }
}

// Error 400
{
  detail: "Email already registered" | "Username already taken"
}
```

#### POST /api/auth/login
```typescript
// Request
{
  email: string
  password: string
}

// Response 200
{
  access_token: string
  refresh_token: string
  token_type: "bearer"
  user: UserResponse
}

// Error 401
{
  detail: "Incorrect email or password"
}

// Error 403
{
  detail: "User account is not active"
}
```

---

### Competition Endpoints

#### POST /api/competitions
```typescript
// Request
{
  name: string
  description?: string
  mode: "daily_picks" | "fixed_teams"
  league_id: string
  start_date: string  // ISO 8601
  end_date: string
  display_timezone?: string
  visibility?: "public" | "private"
  join_type?: "open" | "requires_approval"
  max_participants?: number
  max_picks_per_day?: number
  max_teams_per_participant?: number
  max_golfers_per_participant?: number
}

// Response 201
{
  id: string
  ...all request fields...
  status: "upcoming" | "active" | "completed"
  creator_id: string
  league_admin_ids: string[]
  winner_user_id: string | null
  created_at: string
  updated_at: string
  participant_count: number
  user_is_participant: boolean
  user_is_admin: boolean
}
```

#### GET /api/competitions
```typescript
// Query Params
?status_filter=upcoming|active|completed
&visibility=public|private

// Response 200
[
  {
    id: string
    name: string
    mode: "daily_picks" | "fixed_teams"
    status: "upcoming" | "active" | "completed"
    league_id: string
    start_date: string
    end_date: string
    visibility: "public" | "private"
    participant_count: number
    max_participants: number | null
    user_is_participant: boolean
  }
]
```

---

### Pick Endpoints

#### POST /api/picks/{competition_id}/daily
```typescript
// Request
{
  game_id: string
  predicted_winner_team_id: string
}

// Response 201
{
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

// Error 400
{
  detail: "Game has already started - picks are locked"
}

// Error 403
{
  detail: "You are not a participant in this competition"
}
```

#### POST /api/picks/{competition_id}/fixed
```typescript
// Request
{
  team_id?: string
  golfer_id?: string
}
// Must provide exactly one

// Response 201
{
  id: string
  user_id: string
  competition_id: string
  team_id: string | null
  golfer_id: string | null
  is_locked: boolean
  locked_at: string | null
  total_points: number
  created_at: string
}

// Error 400
{
  detail: "Competition has already started - selections are locked" |
          "Maximum selections reached" |
          "Team/golfer already selected by another participant"
}
```

---

### Leaderboard Endpoints

#### GET /api/leaderboards/{competition_id}
```typescript
// Query Params
?sort_by=points|accuracy|wins|streak

// Response 200
[
  {
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
]
```

---

### Admin Endpoints

#### GET /api/admin/join-requests/{competition_id}
```typescript
// Query Params
?status_filter=pending|approved|rejected

// Response 200
[
  {
    id: string
    user_id: string
    competition_id: string
    status: "pending" | "approved" | "rejected"
    reviewed_by_user_id: string | null
    reviewed_at: string | null
    rejection_reason: string | null
    created_at: string
  }
]

// Error 403
{
  detail: "Only competition admins can view join requests"
}
```

#### POST /api/admin/join-requests/{request_id}/approve
```typescript
// Request
{}  // No body

// Response 200
{
  message: "Join request approved"
}

// Side Effects
- Creates Participant record
- Creates AuditLog entry
```

#### GET /api/admin/audit-logs
```typescript
// Query Params
?competition_id=uuid
&action_filter=competition_created|score_corrected|...
&limit=50
&offset=0

// Response 200
[
  {
    id: string
    admin_user_id: string
    action: string
    target_type: string
    target_id: string | null
    details: object
    created_at: string
  }
]
```

---

## 📋 Quick Reference

### Most Important Files (Priority Order)

**Backend (Must Understand):**
1. `backend/app/main.py` - Application entry
2. `backend/app/core/config.py` - All settings
3. `backend/app/core/security.py` - Auth logic
4. `backend/app/core/deps.py` - Dependencies
5. `backend/app/models/*.py` - Database schema
6. `backend/app/api/*.py` - API endpoints
7. `backend/app/services/sports_api/sports_service.py` - Multi-API failover

**Frontend (Must Understand):**
1. `frontend/src/App.tsx` - Router
2. `frontend/src/services/authStore.ts` - Auth state
3. `frontend/src/services/api.ts` - HTTP client
4. `frontend/src/pages/Dashboard.tsx` - Example page

**Configuration:**
1. `backend/.env` - Secrets
2. `docker-compose.yml` - Local dev
3. `railway.toml` - Deployment

---

## 🔍 Finding Things Quickly

**"Where is authentication handled?"**
- Backend: `app/api/auth.py` + `app/core/security.py` + `app/core/deps.py`
- Frontend: `services/authStore.ts` + `services/api.ts`

**"Where are database models?"**
- All models: `backend/app/models/*.py`
- Schemas (validation): `backend/app/schemas/*.py`

**"Where is the sports API integration?"**
- `backend/app/services/sports_api/sports_service.py` (orchestrator)
- `backend/app/services/circuit_breaker.py` (fault tolerance)

**"Where are the background jobs?"**
- `backend/app/services/background_jobs.py` (🔴 all stubs)

**"Where is pick submission logic?"**
- Backend: `backend/app/api/picks.py`
- Frontend: `frontend/src/pages/CompetitionDetail.tsx` (TODO)

**"Where is the leaderboard calculated?"**
- `backend/app/api/leaderboards.py` (⚠️ Python, should be SQL)

**"Where are admin functions?"**
- `backend/app/api/admin.py` (join requests, audit logs)

---

**Document Maintained By:** Development Team
**Last Updated:** 2025-01-11
**Review Frequency:** After significant file additions/changes
