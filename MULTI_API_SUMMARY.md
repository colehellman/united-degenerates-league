# Multi-API Failover System - Quick Summary

## 🎯 What Problem Does This Solve?

Sports APIs can:
- **Rate limit** your requests (429 errors)
- **Go down** temporarily (500 errors)
- **Have network issues** (timeouts)
- **Be expensive** (cost per request)

**Our solution:** Use **multiple APIs automatically** so your app never goes down!

## 🔄 How It Works (Simple)

```
User requests game data
    ↓
Try ESPN API
    ↓
❌ ESPN rate limited?
    ↓
Try The Odds API
    ↓
❌ The Odds API down?
    ↓
Try RapidAPI
    ↓
✅ Success! Return data
```

## 🏗️ Architecture

```
┌─────────────────┐
│  Sports Service │  ← Your code calls this
└────────┬────────┘
         │
         ├─→ [Circuit Breaker: ESPN]
         │   └─→ ESPN API Client
         │
         ├─→ [Circuit Breaker: The Odds API]
         │   └─→ The Odds API Client
         │
         └─→ [Circuit Breaker: RapidAPI]
             └─→ RapidAPI Client
```

## 🛡️ Circuit Breaker Pattern

**Problem:** Don't waste time trying a broken API repeatedly

**Solution:** After 5 failures, skip that API for 60 seconds

```
ESPN fails 5 times → Circuit "opens" → Skip ESPN for 60s → Auto retry after 60s
```

**States:**
- **CLOSED** (green) - Working normally
- **OPEN** (red) - Too many failures, skipping
- **HALF_OPEN** (yellow) - Testing if recovered

## 💾 Caching Strategy

**Reduces API calls = Saves money + Improves speed**

| Data Type | Cache Duration |
|-----------|----------------|
| Game schedules | 1 hour |
| Live scores | 1 minute |
| API responses | 5 minutes |

**Stale Data Fallback:**
If ALL APIs fail, return old cached data rather than showing nothing.

## 📊 Example Flow

### Successful Request
```
1. Check Redis cache → ❌ Miss
2. Try ESPN API → ✅ Success!
3. Cache result for 5 minutes
4. Return data to user
```

### Failover Scenario
```
1. Check Redis cache → ❌ Miss
2. Try ESPN API → ❌ Rate limited (429)
3. Try The Odds API → ❌ Timeout
4. Try RapidAPI → ✅ Success!
5. Cache result
6. Return data to user
```

### All APIs Down
```
1. Check Redis cache → ❌ Fresh data miss
2. Try ESPN API → ❌ Circuit OPEN
3. Try The Odds API → ❌ 500 error
4. Try RapidAPI → ❌ Timeout
5. Check Redis for expired data → ✅ Found stale data!
6. Return stale data (better than nothing)
```

## 🚀 Usage in Code

### Fetch Game Schedule
```python
from app.services.sports_api import sports_service

# Automatically uses failover!
games = await sports_service.get_schedule(
    league="NFL",
    start_date=datetime(2025, 11, 20),
    end_date=datetime(2025, 11, 27),
)

# games is a list of GameData objects
for game in games:
    print(f"{game.away_team} @ {game.home_team}")
```

### Fetch Live Scores
```python
# Automatically tries all APIs until one works
live_games = await sports_service.get_live_scores(league="NBA")

for game in live_games:
    print(f"{game.away_team} {game.away_score} - {game.home_score} {game.home_team}")
```

### Check API Health
```python
status = sports_service.get_api_health_status()

print(status)
# {
#   "configured_apis": ["espn", "the_odds_api", "rapidapi"],
#   "circuit_breakers": {...},
#   "cache_status": "connected"
# }
```

## 🔧 Configuration

### Environment Variables

```env
# API Keys
ESPN_API_KEY=your-key
THE_ODDS_API_KEY=your-key
RAPIDAPI_KEY=your-key

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5  # Failures before opening
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60   # Wait time before retry

# Caching
CACHE_SCORES_SECONDS=60
CACHE_SCHEDULE_SECONDS=3600

# Timeouts
API_TIMEOUT_SECONDS=10
API_MAX_RETRIES=3
```

## 📈 Monitoring

### Check Circuit Breaker Status

```bash
GET /api/health/api-status

Response:
{
  "configured_apis": ["espn", "the_odds_api"],
  "circuit_breakers": {
    "espn_schedule": {
      "state": "closed",      ← Working!
      "failure_count": 0
    },
    "the_odds_api_live_scores": {
      "state": "open",        ← Temporarily disabled
      "failure_count": 5,
      "time_until_reset": 45  ← Seconds until retry
    }
  }
}
```

### Reset Circuit Breakers (Admin)

```bash
POST /api/health/reset-circuit-breakers
```

## 🎯 Benefits

1. **High Availability** - App stays up even if APIs go down
2. **Cost Efficient** - Use free APIs when available, paid when needed
3. **Automatic** - No manual intervention required
4. **Intelligent** - Circuit breakers prevent wasting time on broken APIs
5. **Fast** - Caching reduces API calls and improves response time
6. **Observable** - Health endpoints show exactly what's working

## 💰 Cost Optimization

**Strategy 1: Free APIs First**
```python
# Configure only free APIs
THE_ODDS_API_KEY=... (500 free requests/month)
# MLB and NHL APIs are completely free
```

**Strategy 2: Increase Cache Times**
```env
CACHE_SCHEDULE_SECONDS=7200  # 2 hours instead of 1
```

**Strategy 3: Use Paid API as Backup**
```python
# Primary: Free APIs
# Fallback: ESPN (paid) only when free APIs fail
```

## 🐛 Common Issues

### Issue: "All APIs failed"

**Cause:** All APIs are rate limited or down

**Solution:**
- Check API keys are valid
- Wait for rate limits to reset
- Add more API providers
- Check stale cache is being returned

### Issue: Circuit breaker stuck OPEN

**Cause:** API had failures, circuit opened

**Solution:**
- Wait 60 seconds for auto-reset
- Or manually reset via `/api/health/reset-circuit-breakers`
- Fix underlying API issue (check key, rate limits)

### Issue: Slow responses

**Cause:** All APIs timing out

**Solution:**
- Check network connectivity
- Increase `API_TIMEOUT_SECONDS`
- Ensure Redis caching is working
- Check API status pages

## 📚 Files Created

```
backend/app/services/
  ├── circuit_breaker.py          ← Circuit breaker implementation
  └── sports_api/
      ├── __init__.py
      ├── base.py                  ← Abstract base class
      ├── espn_client.py           ← ESPN API implementation
      ├── theodds_client.py        ← The Odds API implementation
      ├── rapidapi_client.py       ← RapidAPI implementation
      └── sports_service.py        ← Main service with failover logic

backend/app/api/
  └── health.py                    ← API health endpoints
```

## 🚦 Quick Start

1. **Add at least one API key to `.env`:**
   ```env
   THE_ODDS_API_KEY=your-free-key
   ```

2. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

3. **Check logs:**
   ```bash
   docker-compose logs backend | grep "SportsDataService"
   ```

4. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/api/health/api-status
   ```

5. **Use in your code:**
   ```python
   from app.services.sports_api import sports_service

   games = await sports_service.get_schedule(...)
   ```

## 🎓 Learn More

- **Full Setup Guide:** See `SPORTS_API_SETUP.md`
- **API Documentation:** http://localhost:8000/docs
- **Circuit Breaker Pattern:** https://martinfowler.com/bliki/CircuitBreaker.html

---

**TL;DR:** Your app now uses multiple sports APIs automatically. If one fails, it tries the next. Circuit breakers prevent wasting time on broken APIs. Caching makes it fast and cheap. You're welcome! 🎉
