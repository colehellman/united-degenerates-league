# United Degenerates League - Deployment Checklist

**Last Updated:** 2025-12-12
**Status:** Ready for Production Deployment

---

## Pre-Deployment Checklist

### ✅ Code Complete
- [x] All core features implemented
- [x] Background jobs functional
- [x] API endpoints complete (25+)
- [x] Frontend UI complete
- [x] Error boundaries in place
- [x] Database migrations ready
- [x] Seed data script ready

### ⚠️ Testing Status
- [x] Test framework set up (pytest)
- [x] Critical path tests written
- [ ] Tests passing (need to run)
- [ ] End-to-end testing complete
- [ ] Load testing performed

### ⚠️ Infrastructure
- [x] Docker configuration
- [x] Railway.toml configuration
- [ ] Environment variables documented
- [ ] Database backup strategy
- [ ] Monitoring/alerting configured

---

## Local Testing Checklist

Complete these steps before deploying to production:

### 1. Database Setup ✅

```bash
cd backend

# Run migrations
alembic upgrade head

# Verify tables created
psql -d udl -c "\dt"
# Should show: leagues, teams, golfers, users, competitions,
#              games, participants, picks, fixed_team_selections,
#              join_requests, audit_logs
```

### 2. Seed Data ✅

```bash
# From backend directory
python3 -m scripts.seed_data

# Verify data created
psql -d udl -c "SELECT COUNT(*) FROM teams;"
# Should show: 62 (32 NFL + 30 NBA)

psql -d udl -c "SELECT COUNT(*) FROM users;"
# Should show: 6 (1 admin + 5 test users)

psql -d udl -c "SELECT COUNT(*) FROM competitions;"
# Should show: 3
```

### 3. Backend Tests ⚠️

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/test_critical_paths.py -v

# Run with coverage
pytest tests/test_critical_paths.py --cov=app --cov-report=html

# Expected: All tests pass
```

### 4. Start Backend ✅

```bash
# From backend directory
uvicorn app.main:app --reload

# Verify startup logs show:
# - "INFO:     Uvicorn running on http://127.0.0.1:8000"
# - "INFO:     Started background jobs successfully"
# - "Running background job: update_game_scores"
# - "Running background job: lock_expired_picks"

# Test health endpoint
curl http://localhost:8000/api/health
# Should return 200 OK
```

### 5. Start Frontend ✅

```bash
# From frontend directory
npm install
npm run dev

# Verify startup logs show:
# - "VITE v5.x.x  ready in xxx ms"
# - "Local:   http://localhost:5173/"

# Open browser to http://localhost:5173
# Should see login page
```

### 6. Manual E2E Testing ⚠️

#### Test Flow 1: Registration and Login
- [ ] Navigate to http://localhost:5173/register
- [ ] Register new account (email, username, password)
- [ ] Should redirect to login
- [ ] Login with new credentials
- [ ] Should redirect to dashboard

#### Test Flow 2: Browse and Join Competition
- [ ] Click "Browse Competitions"
- [ ] Should see 3 competitions:
  - NFL Week 15 Picks (ACTIVE)
  - NBA December Championship (UPCOMING)
  - NFL Playoff Fixed Teams (UPCOMING)
- [ ] Click on "NFL Week 15 Picks"
- [ ] Click "Join Competition"
- [ ] Should see competition detail page

#### Test Flow 3: Submit Daily Picks
- [ ] On competition detail page, verify date selector shows
- [ ] Should see list of NFL games
- [ ] For each game, select Home or Away team
- [ ] Click "Submit Picks" at bottom
- [ ] Should see success message
- [ ] Refresh page - picks should persist

#### Test Flow 4: Verify Lock Status
- [ ] Find a game that's scheduled to start soon
- [ ] Make a pick for that game
- [ ] Wait for game start time to pass
- [ ] Refresh page
- [ ] Game should show "LOCKED" badge
- [ ] Pick should be disabled (can't change)

#### Test Flow 5: Leaderboard
- [ ] Scroll down to leaderboard section
- [ ] Should see your username highlighted
- [ ] Should show: Rank, Username, Points, Wins, Losses, Accuracy
- [ ] Make picks and wait for background job
- [ ] Leaderboard should update (30s refresh)

#### Test Flow 6: Fixed Teams Selection
- [ ] Go back to competitions list
- [ ] Click "NFL Playoff Fixed Teams"
- [ ] Join competition
- [ ] Should see list of NFL teams with checkboxes
- [ ] Select 3 teams (max_teams_per_participant=3)
- [ ] Click "Submit Selections"
- [ ] Should see success message
- [ ] Try selecting same teams with different account
- [ ] Should show "Already Selected" (exclusivity)

#### Test Flow 7: Admin Functions
- [ ] Logout
- [ ] Login as admin (admin@udl.com / admin123)
- [ ] Navigate to competition with REQUIRES_APPROVAL join type
- [ ] Should see join requests (if any pending)
- [ ] Approve/reject requests
- [ ] Verify user can now access competition

### 7. Background Jobs Verification ⚠️

```bash
# Watch backend logs while jobs run
# Should see every 60 seconds:
# - "Running background job: update_game_scores"
# - "Running background job: lock_expired_picks"

# Should see every 5 minutes:
# - "Running background job: update_competition_statuses"

# Verify pick locking works:
# 1. Create a game with start time in 1 minute
# 2. Make a pick for that game
# 3. Wait for start time to pass
# 4. Check logs for "Running background job: lock_expired_picks"
# 5. Verify pick.is_locked = true in database

psql -d udl -c "SELECT id, is_locked, locked_at FROM picks WHERE game_id = '<game_id>';"
```

### 8. API Documentation ✅

```bash
# With backend running, visit:
http://localhost:8000/docs

# Verify all endpoints are documented:
# - /api/auth/* (register, login)
# - /api/competitions/* (list, create, join, games, selections)
# - /api/picks/* (daily, my-picks, fixed-teams, my-fixed-selections)
# - /api/leaderboards/{id}
# - /api/admin/* (join requests, audit logs)
# - /api/health/*
```

---

## Production Deployment Checklist

### Railway Deployment Steps

#### 1. Prepare Environment Variables

Create `.env.production` file (DO NOT COMMIT):

```env
# Database (Railway will provide)
DATABASE_URL=${Postgres.DATABASE_URL}

# Redis (Railway will provide)
REDIS_URL=${Redis.REDIS_URL}

# Security (GENERATE NEW VALUES)
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# API Keys (Optional)
ESPN_API_KEY=
THEODDS_API_KEY=
RAPIDAPI_KEY=

# Environment
ENVIRONMENT=production

# CORS (Update with your frontend URL)
ALLOWED_ORIGINS=["https://your-frontend.railway.app"]
```

Generate secure secret key:
```bash
openssl rand -hex 32
```

#### 2. Railway Project Setup

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project (or link existing)
railway init

# Link to project
railway link
```

#### 3. Add PostgreSQL Service

1. Go to Railway dashboard
2. Click "+ New Service"
3. Select "PostgreSQL" from marketplace
4. Wait for provisioning
5. Note the connection string

#### 4. Add Redis Service

1. Click "+ New Service"
2. Select "Redis" from marketplace
3. Wait for provisioning
4. Note the connection string

#### 5. Deploy Backend

1. In Railway dashboard, click "+ New Service"
2. Select "GitHub Repo"
3. Connect your repository
4. Set root directory: `/backend`
5. Add environment variables:
   ```
   DATABASE_URL = ${{Postgres.DATABASE_URL}}
   REDIS_URL = ${{Redis.REDIS_URL}}
   SECRET_KEY = <your-generated-secret>
   ENVIRONMENT = production
   ```
6. Set start command:
   ```bash
   bash -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
   ```
7. Deploy

#### 6. Seed Production Database (One-time)

```bash
# Connect to Railway project
railway link

# Run seed script in Railway environment
railway run python3 -m scripts.seed_data
```

#### 7. Deploy Frontend

1. Click "+ New Service"
2. Select "GitHub Repo"
3. Set root directory: `/frontend`
4. Add environment variable:
   ```
   VITE_API_URL = https://your-backend.railway.app
   ```
5. Set build command: `npm run build`
6. Set start command: `npm run preview`
7. Deploy

#### 8. Configure Custom Domain (Optional)

1. In Railway dashboard, click on frontend service
2. Go to "Settings" → "Domains"
3. Click "Generate Domain" or add custom domain
4. Update CORS in backend environment variables

#### 9. Verify Production Deployment

- [ ] Visit frontend URL
- [ ] Register new account
- [ ] Login
- [ ] Join competition
- [ ] Submit picks
- [ ] Check leaderboard updates
- [ ] Verify background jobs in Railway logs
- [ ] Test all critical flows from E2E checklist

---

## Post-Deployment Monitoring

### Key Metrics to Monitor

1. **API Response Times**
   - 95th percentile < 500ms
   - Median < 200ms

2. **Background Jobs**
   - `update_game_scores`: completes within 30s
   - `lock_expired_picks`: completes within 10s
   - `update_competition_statuses`: completes within 5s
   - Check Railway logs for errors

3. **Database Performance**
   - Query time < 100ms for most queries
   - Connection pool usage < 80%
   - No deadlocks or long-running queries

4. **Error Rates**
   - 4xx errors < 5% of requests
   - 5xx errors < 0.1% of requests
   - Zero critical errors

5. **User Metrics**
   - Registration success rate > 95%
   - Login success rate > 98%
   - Pick submission success rate > 99%

### Recommended Monitoring Tools

1. **Railway Logs**
   - Monitor real-time logs in Railway dashboard
   - Set up log alerts for errors

2. **Sentry (Optional)**
   ```bash
   pip install sentry-sdk[fastapi]
   ```
   ```python
   # In app/main.py
   import sentry_sdk
   sentry_sdk.init(dsn="your-sentry-dsn")
   ```

3. **Uptime Monitoring**
   - Use UptimeRobot or similar
   - Monitor: `https://your-backend.railway.app/api/health`
   - Alert if down > 1 minute

4. **Database Monitoring**
   - Railway provides built-in PostgreSQL metrics
   - Monitor: CPU, Memory, Connections, Query time

---

## Rollback Plan

If deployment fails or critical bugs found:

### Option 1: Rollback via Railway

1. Go to Railway dashboard
2. Click on service
3. Go to "Deployments"
4. Click "Redeploy" on previous working version

### Option 2: Rollback Database Migration

```bash
# Connect to Railway
railway link

# Downgrade one migration
railway run alembic downgrade -1

# Or downgrade to specific version
railway run alembic downgrade <revision>
```

### Option 3: Hotfix Deployment

1. Fix bug locally
2. Test thoroughly
3. Commit and push to GitHub
4. Railway auto-deploys (if enabled)
5. Or manually trigger deployment

---

## Performance Optimization Checklist

After deployment, monitor and optimize:

### Backend

- [ ] Add database indexes for slow queries
- [ ] Implement query result caching in Redis
- [ ] Enable database connection pooling
- [ ] Optimize N+1 queries with eager loading
- [ ] Add rate limiting to prevent abuse

### Frontend

- [ ] Enable production build optimizations
- [ ] Implement code splitting
- [ ] Add service worker for offline support
- [ ] Optimize bundle size (target < 500kb)
- [ ] Lazy load routes and components

### Database

- [ ] Set up automated backups (Railway provides this)
- [ ] Monitor query performance with EXPLAIN
- [ ] Add composite indexes for common queries
- [ ] Consider read replicas for scaling

---

## Security Checklist

### Pre-Deployment

- [x] Passwords hashed with bcrypt
- [x] JWT tokens with expiration
- [ ] HTTPS enforced (Railway provides this)
- [ ] CORS configured correctly
- [x] SQL injection prevention (using ORM)
- [x] XSS prevention (React escapes by default)
- [ ] Rate limiting on auth endpoints
- [ ] Environment secrets not in code
- [ ] `.env` files in `.gitignore`

### Post-Deployment

- [ ] Change all default passwords
- [ ] Rotate SECRET_KEY regularly
- [ ] Set up security headers
- [ ] Enable CSRF protection
- [ ] Monitor for suspicious activity
- [ ] Regular dependency updates
- [ ] Penetration testing

---

## Known Issues & Workarounds

### Issue 1: Token Expiration (30 minutes)

**Problem:** Users are logged out after 30 minutes
**Workaround:** Increase ACCESS_TOKEN_EXPIRE_MINUTES to 1440 (24 hours)
**Proper Fix:** Implement token refresh logic (future update)

### Issue 2: No Pagination

**Problem:** All endpoints return full results
**Impact:** Slow performance with many competitions/users
**Workaround:** Limit competitions to < 100
**Proper Fix:** Add pagination to all list endpoints (future update)

### Issue 3: Leaderboard Calculated in Python

**Problem:** Ranking is calculated in application code
**Impact:** Slower than SQL window functions
**Workaround:** Cache leaderboard in Redis (already implemented)
**Proper Fix:** Use SQL RANK() OVER() (future update)

---

## Support & Troubleshooting

### Common Deployment Issues

**Error: "Alembic migration failed"**
```bash
# Check migration history
railway run alembic current

# Check migration conflicts
railway run alembic history

# Force to head (BE CAREFUL)
railway run alembic stamp head
railway run alembic upgrade head
```

**Error: "Database connection refused"**
```bash
# Verify DATABASE_URL is set correctly
railway variables

# Test database connection
railway run python3 -c "from app.db.session import engine; print('Connected!')"
```

**Error: "Redis connection timeout"**
```bash
# Verify REDIS_URL is set
railway variables

# Test Redis connection
railway run python3 -c "import redis; r = redis.from_url(os.getenv('REDIS_URL')); r.ping(); print('Connected!')"
```

**Error: "Frontend can't reach backend"**
```bash
# Verify VITE_API_URL is correct
# Check CORS settings in backend
# Verify backend is deployed and running
curl https://your-backend.railway.app/api/health
```

### Getting Help

- Check Railway logs for detailed error messages
- Review documentation: `ARCHITECTURE.md`, `CODE_MAP.md`
- Check GitHub issues
- Railway Discord community

---

## Launch Announcement Checklist

Before announcing to friends:

- [ ] All critical tests passing
- [ ] End-to-end testing complete
- [ ] At least 3 test users tested successfully
- [ ] Background jobs verified working
- [ ] Leaderboard updating correctly
- [ ] No critical bugs
- [ ] Frontend deployed and accessible
- [ ] Backend deployed and healthy
- [ ] Database seeded with real leagues/teams
- [ ] Monitoring set up
- [ ] Rollback plan tested

---

## Post-Launch

### Week 1
- [ ] Monitor error rates daily
- [ ] Check user feedback
- [ ] Fix critical bugs immediately
- [ ] Monitor background job performance
- [ ] Check database growth rate

### Week 2-4
- [ ] Implement token refresh
- [ ] Add pagination
- [ ] Optimize slow queries
- [ ] Add admin dashboard UI
- [ ] Implement missing API clients

### Month 2+
- [ ] Add empty states
- [ ] Build onboarding flow
- [ ] Implement push notifications
- [ ] Add social features
- [ ] Mobile app considerations

---

**Status:** Ready for deployment once local E2E testing is complete

**Next Immediate Step:** Run local E2E testing checklist above
