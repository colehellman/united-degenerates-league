# United Degenerates League (UDL)

[![CI](https://github.com/colehellman/united-degenerates-league/actions/workflows/ci.yml/badge.svg)](https://github.com/colehellman/united-degenerates-league/actions/workflows/ci.yml)
[![E2E Tests](https://github.com/colehellman/united-degenerates-league/actions/workflows/e2e.yml/badge.svg)](https://github.com/colehellman/united-degenerates-league/actions/workflows/e2e.yml)
[![Lighthouse CI](https://github.com/colehellman/united-degenerates-league/actions/workflows/lighthouse.yml/badge.svg)](https://github.com/colehellman/united-degenerates-league/actions/workflows/lighthouse.yml)
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://udl-frontend.onrender.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A comprehensive sports prediction and competition platform for friends to compete in daily picks and fixed team challenges across multiple sports leagues (NFL, NBA, MLB, NHL, NCAA, PGA).

## Features

### Core Functionality (v1)
- **Supported Sports**: NFL, NBA, MLB, NHL, NCAA Men's Basketball, NCAA Football, PGA Golf
- **Two Game Modes**:
  - **Daily Picks**: Pick winners for upcoming games with daily limits
  - **Fixed Teams**: Select teams pre-season and track their performance
- **Live Scoring & Standings**: Real-time score updates with comprehensive leaderboards
- **Competition Management**: Create public/private competitions with customizable rules
- **Invite System**: Share invite links to bring friends into competitions
- **Admin Tools**: Global and league-specific admin roles with audit logging
- **Mobile-First Design**: Responsive UI optimized for all device sizes

### Technical Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL 15+ (async with SQLAlchemy 2.0)
- Redis (caching)
- APScheduler (background jobs)
- JWT Authentication
- Alembic (database migrations)

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- TanStack Query (data fetching)
- React Router (navigation)
- Zustand (state management)
- Vitest (testing)

**Infrastructure:**
- Docker Compose (local development and production)
- PostgreSQL, Redis containers
- Hot-reload for development

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Git
- (Optional) Node.js 20+ and Python 3.11+ for local development without Docker

### Quick Start with Docker

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd udl
   ```

2. **Create environment file:**
   ```bash
   cp backend/.env.example backend/.env
   ```

   Edit `backend/.env` and set your secrets:
   ```env
   SECRET_KEY=your-super-secret-key-here-change-this
   # Add your sports API keys here if you have them
   THE_ODDS_API_KEY=
   ESPN_API_KEY=
   RAPIDAPI_KEY=
   ```

3. **Start all services:**
   ```bash
   docker-compose up --build
   ```

   This will start:
   - PostgreSQL database (port 5432)
   - Redis cache (port 6379)
   - Backend API (port 8000)
   - Frontend app (port 3000)

4. **Run database migrations:**
   ```bash
   # In a new terminal
   docker-compose exec backend alembic upgrade head
   ```

5. **Seed the database with sample data:**
    ```bash
    # In the same terminal
    docker-compose exec backend python -m scripts.seed_data
    ```

6. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development (without Docker)

**Backend (Python 3.11 required — matches Dockerfile and CI):**
```bash
cd backend

# Create virtual environment with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

You'll need PostgreSQL and Redis running locally or update the `.env` file to point to remote instances.

## Project Structure

```
udl/
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── api/                 # API endpoints (auth, competitions, picks, etc.)
│   │   ├── core/                # Core utilities (config, security, dependencies)
│   │   ├── db/                  # Database session and connection
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business logic and background jobs
│   │   └── main.py              # FastAPI application entry point
│   ├── scripts/
│   │   └── seed_data.py
│   ├── tests/                   # Backend tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API client and services
│   │   ├── hooks/               # Custom React hooks
│   │   ├── types/               # TypeScript type definitions
│   │   ├── utils/               # Utility functions
│   │   ├── styles/              # CSS and Tailwind styles
│   │   ├── tests/               # Frontend tests
│   │   ├── App.tsx              # Main app component
│   │   └── main.tsx             # Entry point
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── mcp_server/                  # MCP server for Playwright integration
├── docker-compose.yml
└── README.md
```

## Database Schema

<!-- AUTO:MODELS:START -->
Key models:
- **AuditLog**: Immutable audit log for admin actions
- **BugReport**: User-submitted bug reports
- **Competition**: Represents a competition (Daily Picks or Fixed Teams)
- **Game**: Individual games/matches
- **InviteLink**: A shareable invite link for a competition.
- **League**: Sports leagues (NFL, NBA, etc.)
- **Team**: Teams within leagues
- **Golfer**: PGA golfers within a league
- **Participant**: Represents a user's participation in a specific competition
- **JoinRequest**: Join request for competitions with requiresApproval join type
- **Pick**: Daily Picks - user's prediction for a specific game
- **FixedTeamSelection**: Fixed Teams - user's pre-selected teams or golfers for the entire competition
- **User**: Authentication and user management
<!-- AUTO:MODELS:END -->

## API Endpoints

<!-- AUTO:ENDPOINTS:START -->
### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login with email and password
- `POST /api/auth/refresh` - Exchange a valid refresh token for new access + refresh tokens
- `POST /api/auth/logout` - Clear auth cookies and blacklist the refresh token server-side

### Users
- `GET /api/users/me` - Get current user profile
- `PATCH /api/users/me` - Update current user profile
- `POST /api/users/me/change-password` - Change user password
- `DELETE /api/users/me` - Request account deletion (30-day grace period)
- `POST /api/users/me/cancel-deletion` - Cancel account deletion request

### Leagues
- `GET /api/leagues` - List all available leagues

### Competitions
- `POST /api/competitions` - Create a new competition
- `GET /api/competitions` - List all competitions accessible to the current user
- `GET /api/competitions/{competition_id}` - Get a specific competition
- `PATCH /api/competitions/{competition_id}` - Update a competition (admins only)
- `DELETE /api/competitions/{competition_id}` - Delete a competition (global admins only)
- `POST /api/competitions/{competition_id}/join` - Join a competition or request to join. Optionally pass an invite_token
- `GET /api/competitions/{competition_id}/invite-links` - List invite links for a competition. Participants see own, admins see all
- `GET /api/competitions/{competition_id}/games` - Get games for a competition, optionally filtered by date
- `POST /api/competitions/{competition_id}/sync-games` - Force an immediate ESPN game sync for a specific competition
- `GET /api/competitions/{competition_id}/available-selections` - Get available teams/golfers for fixed team selection

### Invites
- `GET /api/invite/{token}` - Resolve an invite token to competition info. No auth required

### Picks
- `GET /api/picks/{competition_id}/my-picks` - Get current user's daily picks for a competition

### Leaderboards
- `GET /api/leaderboards/{competition_id}` - Get leaderboard for a competition

### Admin
- `PATCH /api/admin/users/{user_id}/status` - Ban, suspend, or reactivate a user account (global admin only)
- `PATCH /api/admin/users/{user_id}/role` - Change a user's role (global admin only)
- `GET /api/admin/users` - List all non-deleted users on the platform (paginated, global admin only)
- `POST /api/admin/competitions/{competition_id}/status` - Force a competition status change (global admin only)
- `POST /api/admin/games/{game_id}/correct-score` - Correct a game's score and re-score all picks (global admin only)
- `POST /api/admin/games/{game_id}/rescore` - Manually re-score all picks for a game (global admin only)
- `POST /api/admin/competitions/{competition_id}/winner` - Designate a competition winner (global admin only)
- `DELETE /api/admin/competitions/{competition_id}/participants/{user_id}` - Remove a participant from a competition (competition admin or global admin)
- `POST /api/admin/competitions/{competition_id}/admins` - Add a user as a competition admin (competition admin or global admin)
- `DELETE /api/admin/competitions/{competition_id}/admins/{admin_user_id}` - Remove a user from competition admin list (competition admin or global admin)
- `GET /api/admin/join-requests/{competition_id}` - Get join requests for a competition (admins only)
- `POST /api/admin/join-requests/{request_id}/approve` - Approve a join request (admins only)
- `POST /api/admin/join-requests/{request_id}/reject` - Reject a join request (admins only)
- `POST /api/admin/sync-games` - Trigger an immediate game sync from ESPN (global admins only)
- `GET /api/admin/audit-logs` - Get audit logs (admins only)
- `GET /api/admin/stats` - Basic platform analytics (global admin only)
- `GET /api/admin/competitions` - List all competitions with participant counts (global admin only)

### Bug Reports
- `POST /api/bug-reports` - Submit a bug report. Any authenticated user can file a report
- `GET /api/bug-reports/mine` - Return bug reports filed by the current user, newest first
- `GET /api/bug-reports` - Return all bug reports (paginated). Global admins only
- `PATCH /api/bug-reports/{report_id}` - Update a bug report's status. Global admins only

### Health & Monitoring
- `GET /health` - Deep health check — verifies database and Redis connectivity
- `GET /` - Root endpoint
- `GET /api/health/api-status` - Get status of all sports data APIs and circuit breakers
- `POST /api/health/reset-circuit-breakers` - Manually reset all circuit breakers

### WebSocket
- `WS /ws/scores` - Stream live score updates to connected clients

Full API documentation available at `/docs` when the backend is running.
<!-- AUTO:ENDPOINTS:END -->

## Background Jobs

The application runs several background jobs:

1. **Score Updates** (every 60 seconds):
   - Fetch latest scores from sports APIs
   - Update game records
   - Recalculate pick results and points
   - Invalidate caches

2. **Competition Status Updates** (every 5 minutes):
   - Transition competitions from `upcoming` → `active` → `completed`
   - Lock fixed team selections when competition starts
   - Freeze standings when competition ends

3. **Pick Locking** (every 60 seconds):
   - Lock picks for games that have started
   - Prevent editing of locked picks

4. **Account Cleanup** (daily at 2 AM UTC):
   - Permanently delete accounts after 30-day grace period
   - Anonymize historical data

## Sports Data API Integration

The application integrates with external sports APIs for game schedules and scores.

**API Keys** (add to `backend/.env` — all optional, system uses multi-provider failover):
- `THE_ODDS_API_KEY` — free tier available, recommended
- `ESPN_API_KEY` — paid, most reliable
- `RAPIDAPI_KEY` — paid, good coverage
- MLB and NHL Stats APIs require no key and work automatically

**API Integration Features:**
- Automatic schedule fetching
- Real-time score updates
- Caching strategy (60s for active games, 5min for inactive)
- Error handling with fallback to cached data
- Rate limiting and request throttling

**Note:** You'll need to obtain API keys from your chosen sports data providers. Free tiers are available for most providers but may have rate limits.

## Mobile Responsiveness

The application is designed mobile-first with responsive breakpoints:
- **360px**: Small phones (Samsung Galaxy S8)
- **375px**: iPhone SE, iPhone 12/13 mini
- **414px**: iPhone Pro Max
- **768px**: Tablets (iPad)
- **1024px**: Small laptops
- **1440px+**: Desktop

**Mobile Features:**
- Sticky submit bar for picks
- Collapsible date sections
- Large tap targets (44x44px minimum)
- Touch-optimized interactions
- Hamburger navigation on small screens

## Testing

**Backend Tests:**
```bash
cd backend
source .venv/bin/activate
pytest
```

**Frontend Tests:**
```bash
cd frontend
npm test
```

## Production Deployment

### Environment Variables

Ensure all production environment variables are set:

```env
# Security
SECRET_KEY=<strong-random-key>
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Redis
REDIS_URL=redis://host:6379/0

# Sports APIs
THE_ODDS_API_KEY=<your-key>
# ... etc

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Docker Production Build

```bash
# Build production images
docker-compose build

# Start services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head
```

### Health Checks

- Backend health: `GET /health`
- API documentation: `GET /docs`
- Check logs: `docker-compose logs -f backend`

## Troubleshooting

**Database connection errors:**
- Ensure PostgreSQL is running: `docker-compose ps`
- Check DATABASE_URL in `.env`
- Verify migrations: `docker-compose exec backend alembic current`

**Frontend can't connect to backend:**
- Check backend is running on port 8000
- Verify VITE_API_URL environment variable
- Check CORS settings in backend

**Background jobs not running:**
- Check backend logs: `docker-compose logs backend`
- Verify APScheduler is started (should see log messages)

**Sports API errors:**
- Verify API keys in `.env`
- Check rate limits
- Review cached data fallback in logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
- Create an issue on GitHub
- Check the API documentation at `/docs`
- Review the specification document for detailed requirements

## Roadmap

### v1 (Current)
- Core sports leagues (NFL, NBA, MLB, NHL, NCAA, PGA)
- Daily Picks and Fixed Teams modes
- Live scoring and leaderboards
- Admin dashboard and audit logging
- Invite link sharing for competitions
- Multi-provider sports API failover with circuit breakers
- WebSocket live score updates

### v2 (Planned)
**New Leagues & Competitions:**
- MLS (Major League Soccer)
- EPL (English Premier League)
- UCL / Europa League

**Social & Engagement:**
- Friend/follower system with "Friends only" leaderboard filter
- League chat and trash talk features
- Badges, achievements, and gamification
- Hot streak and win streak tracking

**Analytics & Data:**
- Advanced statistics (head-to-head records, prediction accuracy trends)
- More sophisticated data visualizations
- Multi-season tracking and historical comparisons
- Export league history as PDF/CSV

**Notifications:**
- Email notifications (opt-in) for picks, results, and competition updates
- Push notifications for mobile

**UX Improvements:**
- Combined multi-league view (all games across leagues in one view)
- User-selectable display timezone
- "In Progress" live game status badges
- Account reactivation emails for soft-deleted accounts

---

Built with FastAPI, React, and PostgreSQL | Mobile-First Design
