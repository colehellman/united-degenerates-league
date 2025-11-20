# United Degenerates League (UDL)

A comprehensive sports prediction and competition platform for friends to compete in daily picks and fixed team challenges across multiple sports leagues (NFL, NBA, MLB, NHL, NCAA, PGA).

## Features

### Core Functionality (v1)
- **Supported Sports**: NFL, NBA, MLB, NHL, NCAA Men's Basketball, NCAA Football, PGA Golf
- **Two Game Modes**:
  - **Daily Picks**: Pick winners for upcoming games with daily limits
  - **Fixed Teams**: Select teams pre-season and track their performance
- **Live Scoring & Standings**: Real-time score updates with comprehensive leaderboards
- **Competition Management**: Create public/private competitions with customizable rules
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
   # Add your sports API keys here
   ESPN_API_KEY=your-espn-api-key
   SPORTSDATA_API_KEY=your-sportsdata-key
   # ... etc
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

5. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development (without Docker)

**Backend:**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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
│   │   ├── App.tsx              # Main app component
│   │   └── main.tsx             # Entry point
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── docker-compose.yml
└── README.md
```

## Database Schema

Key models:
- **User**: Authentication and user management
- **Competition**: Represents a competition (Daily Picks or Fixed Teams)
- **League**: Sports leagues (NFL, NBA, etc.)
- **Team**: Teams within leagues
- **Golfer**: PGA golfers
- **Game**: Individual games/matches
- **Pick**: Daily picks for games
- **FixedTeamSelection**: Pre-season team/golfer selections
- **Participant**: User participation in competitions
- **JoinRequest**: Join requests for private competitions
- **AuditLog**: Immutable audit trail of admin actions

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login

### Users
- `GET /api/users/me` - Get current user profile
- `PATCH /api/users/me` - Update user profile
- `POST /api/users/me/change-password` - Change password
- `DELETE /api/users/me` - Request account deletion

### Competitions
- `POST /api/competitions` - Create competition
- `GET /api/competitions` - List competitions
- `GET /api/competitions/{id}` - Get competition details
- `PATCH /api/competitions/{id}` - Update competition (admins only)
- `DELETE /api/competitions/{id}` - Delete competition (global admins only)
- `POST /api/competitions/{id}/join` - Join competition

### Picks
- `POST /api/picks/{competition_id}/daily` - Submit daily pick
- `GET /api/picks/{competition_id}/daily` - Get user's daily picks
- `POST /api/picks/{competition_id}/fixed-teams` - Submit fixed team selection
- `GET /api/picks/{competition_id}/fixed-teams` - Get user's fixed team selections

### Leaderboards
- `GET /api/leaderboards/{competition_id}` - Get competition leaderboard

### Admin
- `GET /api/admin/join-requests/{competition_id}` - Get join requests (admins only)
- `POST /api/admin/join-requests/{id}/approve` - Approve join request
- `POST /api/admin/join-requests/{id}/reject` - Reject join request
- `GET /api/admin/audit-logs` - Get audit logs

Full API documentation available at `/docs` when the backend is running.

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

**Required API Keys** (add to `backend/.env`):
- ESPN API or similar for NFL, NBA, MLB, NHL, NCAA
- PGA Tour API for golf tournaments

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
pytest
```

**Frontend Tests:**
```bash
cd frontend
npm test
```

**Manual Testing Checklist:**
- [ ] User registration and login
- [ ] Competition creation (both modes)
- [ ] Joining competitions
- [ ] Submitting daily picks
- [ ] Fixed team selection
- [ ] Leaderboard updates
- [ ] Admin functions
- [ ] Mobile responsiveness at all breakpoints
- [ ] Real-time lock status updates

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
ESPN_API_KEY=<your-key>
SPORTSDATA_API_KEY=<your-key>
# ... etc

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
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

### v2 (Future)
- Additional leagues (MLS, EPL, UCL)
- Advanced analytics and statistics
- Badges and achievements
- Social features (league chat, trash talk)
- Email/push notifications
- Multi-season tracking
- Export functionality (PDF/CSV)

---

Built with FastAPI, React, and PostgreSQL | Mobile-First Design | Production-Ready

## 🔄 Multi-API Failover System (NEW!)

The app now uses **multiple sports data APIs** with automatic failover to ensure high availability:

### Features
- ✅ **Automatic Failover** - If one API is rate-limited or down, automatically try the next
- ✅ **Circuit Breaker Pattern** - Temporarily skip failing APIs to prevent cascading failures
- ✅ **Smart Caching** - Redis caching reduces API calls and improves performance
- ✅ **Stale Data Fallback** - Return cached data if all APIs fail (better than nothing!)
- ✅ **Real-time Monitoring** - Health endpoints show status of all APIs and circuit breakers

### Supported APIs
1. **ESPN API** (Primary)
2. **The Odds API** (Secondary)
3. **RapidAPI Sports** (Tertiary)
4. **MLB Stats API** (Free, no key required)
5. **NHL Stats API** (Free, no key required)

### Quick Setup

Add at least one API key to `backend/.env`:

```env
# Recommended: The Odds API (has free tier)
THE_ODDS_API_KEY=your-odds-api-key-here

# Optional: ESPN (paid, more reliable)
ESPN_API_KEY=your-espn-api-key-here

# Optional: RapidAPI (paid, good coverage)
RAPIDAPI_KEY=your-rapidapi-key-here
```

**Free APIs (MLB, NHL) work automatically with no keys required!**

### Monitoring

Check API health status:
```bash
GET /api/health/api-status
```

See detailed setup guide: **[SPORTS_API_SETUP.md](SPORTS_API_SETUP.md)**

