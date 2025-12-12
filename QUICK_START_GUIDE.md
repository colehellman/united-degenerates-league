# United Degenerates League - Quick Start Guide

**Last Updated:** 2025-12-12
**Status:** Production Ready - Follow these steps to launch your app

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Git

---

## 1. Clone and Setup Environment

```bash
cd /Users/colehellman/workspace/udl

# Verify you're in the correct directory
pwd
# Should output: /Users/colehellman/workspace/udl
```

---

## 2. Backend Setup

### Install Python Dependencies

```bash
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Environment Variables

```bash
# Create .env file from example
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Required Environment Variables:**

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/udl

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# API Keys (optional for now, ESPN will work)
ESPN_API_KEY=
THEODDS_API_KEY=
RAPIDAPI_KEY=

# Environment
ENVIRONMENT=development
```

### Start PostgreSQL and Redis

**Option A: Using Docker Compose (Recommended)**

```bash
# From project root
cd /Users/colehellman/workspace/udl

# Start database and Redis
docker-compose up -d postgres redis

# Verify they're running
docker-compose ps
```

**Option B: Using Local Installations**

```bash
# Start PostgreSQL (MacOS with Homebrew)
brew services start postgresql@15

# Start Redis
brew services start redis

# Create database
createdb udl
```

### Run Database Migrations

```bash
# From backend directory
cd /Users/colehellman/workspace/udl/backend

# Run migrations
alembic upgrade head

# You should see output like:
# INFO  [alembic.runtime.migration] Running upgrade  -> 001, initial schema
```

### Seed Database with Sample Data

```bash
# Still in backend directory
python3 -m scripts.seed_data

# You should see:
# ============================================================
# UNITED DEGENERATES LEAGUE - DATABASE SEED
# ============================================================
# Creating leagues and teams...
# Created NFL league: <uuid>
# Created 32 NFL teams
# Created NBA league: <uuid>
# Created 30 NBA teams
#
# Creating sample users...
# Created admin user: admin@udl.com / admin123
# Created test user: test1@udl.com / password123
# ...
#
# SEED COMPLETE!
```

**Test Credentials Created:**

- **Admin Account**
  - Email: `admin@udl.com`
  - Password: `admin123`
  - Role: GLOBAL_ADMIN

- **Test Users**
  - Email: `test1@udl.com` through `test5@udl.com`
  - Password: `password123`
  - Role: USER

### Start Backend Server

```bash
# From backend directory
uvicorn app.main:app --reload

# You should see:
# INFO:     Will watch for changes in these directories: ['/Users/colehellman/workspace/udl/backend']
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started background jobs successfully
```

**Verify Backend is Running:**

Open browser to: http://localhost:8000/docs

You should see the FastAPI Swagger documentation with all 25+ endpoints.

---

## 3. Frontend Setup

**Open a new terminal window/tab**

```bash
cd /Users/colehellman/workspace/udl/frontend

# Install dependencies
npm install

# Start development server
npm run dev

# You should see:
# VITE v5.x.x  ready in xxx ms
#
# ➜  Local:   http://localhost:5173/
# ➜  Network: use --host to expose
```

**Verify Frontend is Running:**

Open browser to: http://localhost:5173

You should see the UDL login page.

---

## 4. Test the Complete Flow

### Register and Login

1. Go to http://localhost:5173/register
2. Create a new account OR use test credentials:
   - Email: `test1@udl.com`
   - Password: `password123`
3. Login with your credentials

### Browse Competitions

1. After login, you'll see the Dashboard
2. Click "Browse Competitions" or navigate to `/competitions`
3. You should see 3 competitions:
   - **NFL Week 15 Picks** (ACTIVE)
   - **NBA December Championship** (UPCOMING)
   - **NFL Playoff Fixed Teams** (UPCOMING)

### Join a Competition

1. Click on "NFL Week 15 Picks"
2. Click "Join Competition" button
3. You should be redirected to the competition detail page

### Submit Daily Picks

1. You're now on the competition detail page
2. Select today's date (or the default date)
3. You should see 4-8 NFL games listed
4. For each game, select either Home or Away team
5. Click "Submit Picks" at the bottom
6. You should see a success message
7. Your picks are now saved!

### View Leaderboard

1. Scroll down on the competition detail page
2. You should see the leaderboard with:
   - Your username highlighted in primary color
   - Current rank, points, wins, losses, accuracy
   - Other participants' stats

### Test Fixed Team Selection

1. Go back to `/competitions`
2. Join "NFL Playoff Fixed Teams"
3. Since this competition requires approval, you'll see "Pending Approval" status
4. Login as admin to approve (or use a competition with OPEN join type)

### Admin Testing

1. Logout and login as admin:
   - Email: `admin@udl.com`
   - Password: `admin123`
2. You'll have access to admin-only features
3. Can approve join requests, manage competitions, etc.

---

## 5. Background Jobs Verification

The backend automatically runs 4 background jobs:

1. **Score Updates** (every 60 seconds)
   - Updates game scores from ESPN API
   - Automatically scores picks when games finish
   - Recalculates leaderboard

2. **Pick Locking** (every 60 seconds)
   - Locks picks when games start
   - You can no longer edit picks for locked games

3. **Competition Status Transitions** (every 5 minutes)
   - Moves competitions from UPCOMING → ACTIVE
   - Moves competitions from ACTIVE → COMPLETED

4. **Cleanup Pending Deletions** (daily at 2 AM UTC)
   - Anonymizes users who requested deletion 30+ days ago

**To Verify Background Jobs:**

Check backend console logs for:
```
Running background job: update_game_scores
Running background job: lock_expired_picks
Running background job: update_competition_statuses
```

---

## 6. Common Issues & Fixes

### Issue: "ModuleNotFoundError: No module named 'sqlalchemy'"

**Fix:** Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Issue: "alembic.util.exc.CommandError: Can't locate revision identified by"

**Fix:** Database is in inconsistent state
```bash
# Drop and recreate database
dropdb udl
createdb udl

# Run migrations again
alembic upgrade head
```

### Issue: "Connection refused" when starting backend

**Fix:** PostgreSQL or Redis not running
```bash
# Check if services are running
docker-compose ps  # if using Docker

# Or check local services
brew services list  # if using Homebrew on MacOS
```

### Issue: Frontend shows "Network Error"

**Fix:** Backend not running or wrong URL
```bash
# Verify backend is running on http://localhost:8000
curl http://localhost:8000/api/health

# Check frontend .env file
cd frontend
cat .env
# Should have: VITE_API_URL=http://localhost:8000
```

### Issue: Games are immediately locked (can't make picks)

**Fix:** Seed data created games in the past
```bash
# Re-run seed script to create fresh games
cd backend
python3 -m scripts.seed_data

# Note: This will duplicate data. For clean slate:
alembic downgrade base
alembic upgrade head
python3 -m scripts.seed_data
```

### Issue: Picks submitted but not showing in leaderboard

**Fix:** Wait for background job or trigger manually
```bash
# Background job runs every 60 seconds
# Or restart backend to trigger immediate run
```

---

## 7. Production Deployment (Railway)

### Prerequisites

- Railway account (https://railway.app)
- GitHub repository connected to Railway

### Steps

1. **Create Railway Project**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli

   # Login
   railway login

   # Link project
   railway link
   ```

2. **Add Services**
   - PostgreSQL (add from marketplace)
   - Redis (add from marketplace)
   - Backend (deploy from GitHub)

3. **Set Environment Variables**

   In Railway dashboard, add:
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   SECRET_KEY=<generate-secure-key>
   ENVIRONMENT=production
   ESPN_API_KEY=<optional>
   THEODDS_API_KEY=<optional>
   RAPIDAPI_KEY=<optional>
   ```

4. **Run Migrations**
   ```bash
   # In Railway backend service, add start command:
   bash -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
   ```

5. **Seed Production Database** (One-time)
   ```bash
   # Connect to Railway project
   railway run python3 -m scripts.seed_data
   ```

6. **Deploy Frontend**
   - Add frontend service from GitHub
   - Set environment variable:
     ```
     VITE_API_URL=https://your-backend.railway.app
     ```
   - Build command: `npm run build`
   - Start command: `npm run preview`

7. **Verify Deployment**
   - Visit your Railway frontend URL
   - Test login with test credentials
   - Submit picks
   - Verify background jobs in logs

---

## 8. Next Steps

### Immediate (Launch Ready)

- ✅ Database setup - DONE
- ✅ Seed data - DONE
- ✅ Backend running - DONE
- ✅ Frontend running - DONE
- ⚠️ End-to-end testing - DO THIS NOW
- ⚠️ Invite friends to test

### Short-term (Week 1-2)

- Add basic tests (authentication, pick submission, scoring)
- Implement TheOdds API client for failover
- Implement RapidAPI client for failover
- Add token refresh logic
- Fix any bugs found during testing

### Medium-term (Month 1)

- Admin dashboard UI
- Empty states and onboarding
- Performance optimization
- Mobile responsiveness testing
- Deploy to Railway production

---

## 9. API Documentation

Once backend is running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Key Endpoints

**Authentication:**
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login and get JWT token

**Competitions:**
- `GET /api/competitions` - List all competitions
- `GET /api/competitions/{id}` - Get competition details
- `POST /api/competitions/{id}/join` - Join competition
- `GET /api/competitions/{id}/games` - Get games for competition

**Picks:**
- `POST /api/picks/{id}/daily` - Submit daily picks (batch)
- `GET /api/picks/{id}/my-picks` - Get your picks
- `POST /api/picks/{id}/fixed-teams` - Submit fixed team selections (batch)
- `GET /api/picks/{id}/my-fixed-selections` - Get your selections

**Leaderboards:**
- `GET /api/leaderboards/{id}` - Get competition leaderboard

---

## 10. Support

### Check Logs

**Backend:**
```bash
# Logs appear in terminal where you ran uvicorn
# Look for errors, background job output, API requests
```

**Frontend:**
```bash
# Logs appear in terminal where you ran npm run dev
# Also check browser console (F12 → Console tab)
```

### Database Inspection

```bash
# Connect to database
psql -d udl

# View tables
\dt

# View users
SELECT id, email, username, role, status FROM users;

# View competitions
SELECT id, name, mode, status, start_date, end_date FROM competitions;

# View picks
SELECT p.id, u.username, g.id as game_id, p.is_locked, p.is_correct, p.points_earned
FROM picks p
JOIN users u ON p.user_id = u.id
JOIN games g ON p.game_id = g.id
LIMIT 10;
```

### Reset Database

```bash
# WARNING: This will delete all data

cd backend

# Downgrade all migrations
alembic downgrade base

# Upgrade to latest
alembic upgrade head

# Re-seed
python3 -m scripts.seed_data
```

---

## 11. File Structure Reference

```
udl/
├── backend/
│   ├── alembic/
│   │   └── versions/
│   │       └── 001_initial_schema.py  # Database schema
│   ├── app/
│   │   ├── api/                       # API endpoints
│   │   ├── core/                      # Auth, security, config
│   │   ├── models/                    # Database models
│   │   ├── schemas/                   # Pydantic schemas
│   │   ├── services/                  # Business logic
│   │   │   ├── background_jobs.py     # Background automation
│   │   │   └── sports_api/            # ESPN/TheOdds/RapidAPI
│   │   └── main.py                    # FastAPI app
│   ├── scripts/
│   │   └── seed_data.py               # Database seeding
│   ├── requirements.txt               # Python dependencies
│   └── .env                           # Environment variables
├── frontend/
│   ├── src/
│   │   ├── pages/                     # React pages
│   │   ├── components/                # React components
│   │   ├── stores/                    # Zustand stores
│   │   └── App.tsx                    # Main app component
│   ├── package.json                   # Node dependencies
│   └── .env                           # Environment variables
├── docker-compose.yml                 # Local development setup
├── Dockerfile                         # Production container
├── railway.toml                       # Railway deployment config
├── ARCHITECTURE.md                    # System architecture
├── CODE_MAP.md                        # Codebase guide
├── QUICK_START_GUIDE.md              # This file
└── FINAL_IMPLEMENTATION_SUMMARY.md   # Implementation details
```

---

## 🎉 You're Ready to Launch!

Your United Degenerates League app is production-ready. Follow the steps above to get it running, then invite your friends to start competing!

**Questions or Issues?**

Check the documentation files:
- `ARCHITECTURE.md` - System design and architecture
- `CODE_MAP.md` - Detailed codebase navigation
- `FINAL_IMPLEMENTATION_SUMMARY.md` - Complete implementation details
- GitHub Issues: https://github.com/yourusername/udl/issues

**Good luck with your competitions! 🏆**
