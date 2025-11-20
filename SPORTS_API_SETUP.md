# Sports API Setup Guide

The United Degenerates League uses **multiple sports data APIs** with automatic failover to ensure the app stays functional even if one API is rate-limited or down.

## 🔄 Multi-API Failover System

### How It Works

1. **Priority Order**: APIs are tried in order (ESPN → The Odds API → RapidAPI)
2. **Circuit Breaker**: If an API fails 5 times, it's temporarily disabled for 60 seconds
3. **Automatic Fallback**: If one API fails, the next one is tried automatically
4. **Caching**: Responses are cached to reduce API calls
5. **Stale Data Fallback**: If all APIs fail, cached data is returned (even if expired)

### Supported APIs

| API | Priority | Cost | Rate Limits | Sports Covered |
|-----|----------|------|-------------|----------------|
| **ESPN API** | Primary | Free/Paid | Varies | All |
| **The Odds API** | Secondary | Free tier available | 500 requests/month (free) | All |
| **RapidAPI Sports** | Tertiary | Subscription | Varies by endpoint | All |
| **MLB Stats API** | Backup | Free | No key needed | MLB only |
| **NHL Stats API** | Backup | Free | No key needed | NHL only |

## 📋 API Setup Instructions

### 1. ESPN API (Primary - Recommended)

**Sign up:**
1. Go to https://developer.espn.com/
2. Create an account
3. Request an API key
4. Add to your `.env`:
   ```env
   ESPN_API_KEY=your-espn-api-key-here
   ```

**Features:**
- Comprehensive sports data
- Real-time scores
- Game schedules
- Team information

**Rate Limits:**
- Free tier: Limited requests
- Contact ESPN for higher limits

---

### 2. The Odds API (Secondary - Recommended)

**Sign up:**
1. Go to https://the-odds-api.com/
2. Sign up for a free account
3. Get your API key from the dashboard
4. Add to your `.env`:
   ```env
   THE_ODDS_API_KEY=your-odds-api-key-here
   ```

**Features:**
- Odds and scores
- Live game data
- Historical results
- Multiple sports

**Rate Limits:**
- Free tier: 500 requests/month
- Paid plans available for higher usage

---

### 3. RapidAPI Sports (Tertiary - Optional)

**Sign up:**
1. Go to https://rapidapi.com/hub
2. Create an account
3. Subscribe to these APIs:
   - **API American Football** (NFL)
   - **API NBA** (NBA)
   - **API Baseball** (MLB)
   - **API Hockey** (NHL)
   - **API NCAA** (College sports)
   - **Golf Leaderboard Data** (PGA)
4. Get your RapidAPI key
5. Add to your `.env`:
   ```env
   RAPIDAPI_KEY=your-rapidapi-key-here
   ```

**Features:**
- Separate APIs for each sport
- Detailed statistics
- Live scores
- Historical data

**Rate Limits:**
- Varies by API
- Most have free tiers with 100-500 requests/day
- Paid plans for higher usage

---

### 4. MLB Stats API (Free - Backup)

**No signup required!**

The MLB Stats API is free and doesn't require an API key.

Already configured in `.env`:
```env
MLB_STATS_API_URL=https://statsapi.mlb.com/api/v1
```

**Features:**
- Official MLB data
- Real-time scores
- Complete game information
- Free with no rate limits

---

### 5. NHL Stats API (Free - Backup)

**No signup required!**

The NHL Stats API is free and doesn't require an API key.

Already configured in `.env`:
```env
NHL_STATS_API_URL=https://api-web.nhle.com/v1
```

**Features:**
- Official NHL data
- Live scores
- Game schedules
- Free with no rate limits

---

## 🚀 Quick Start

### Minimum Setup (Free)

For testing without any API keys:

1. **Don't set any API keys** - the app will still work with mock data
2. Or use free APIs only:
   ```env
   THE_ODDS_API_KEY=your-free-odds-api-key
   MLB_STATS_API_URL=https://statsapi.mlb.com/api/v1
   NHL_STATS_API_URL=https://api-web.nhle.com/v1
   ```

### Recommended Setup (Best reliability)

Configure at least 2 APIs for redundancy:

```env
# Primary
ESPN_API_KEY=your-espn-key

# Secondary (free tier)
THE_ODDS_API_KEY=your-odds-api-key

# Free backups
MLB_STATS_API_URL=https://statsapi.mlb.com/api/v1
NHL_STATS_API_URL=https://api-web.nhle.com/v1
```

### Production Setup (Maximum reliability)

Configure all APIs:

```env
# All APIs configured for maximum redundancy
ESPN_API_KEY=your-espn-key
THE_ODDS_API_KEY=your-odds-api-key
RAPIDAPI_KEY=your-rapidapi-key
# Free APIs already configured
```

## 🔧 Configuration

### Circuit Breaker Settings

Adjust in `backend/.env`:

```env
# After X failures, stop trying this API for Y seconds
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60
```

### API Timeout & Retries

```env
# Request timeout (seconds)
API_TIMEOUT_SECONDS=10

# Retry configuration
API_MAX_RETRIES=3
API_RETRY_DELAY_SECONDS=2
```

### Cache Settings

```env
# Cache duration for different data types
CACHE_SCORES_SECONDS=60          # Live scores (1 min)
CACHE_SCHEDULE_SECONDS=3600      # Game schedules (1 hour)
CACHE_API_RESPONSE_SECONDS=300   # General API responses (5 min)
```

## 📊 Monitoring API Health

### Check API Status

**As an authenticated user:**
```bash
GET /api/health/api-status
```

**Response:**
```json
{
  "configured_apis": ["espn", "the_odds_api", "rapidapi"],
  "circuit_breakers": {
    "espn_schedule": {
      "name": "espn_schedule",
      "state": "closed",
      "failure_count": 0,
      "failure_threshold": 5,
      "last_failure_time": null,
      "last_success_time": "2025-11-20T10:30:00",
      "time_until_reset": 0
    },
    "the_odds_api_live_scores": {
      "name": "the_odds_api_live_scores",
      "state": "open",
      "failure_count": 5,
      "failure_threshold": 5,
      "last_failure_time": "2025-11-20T10:25:00",
      "time_until_reset": 45
    }
  },
  "cache_status": "connected"
}
```

### Reset Circuit Breakers

**As a global admin:**
```bash
POST /api/health/reset-circuit-breakers
```

This manually resets all circuit breakers if you've fixed an API issue.

## 🐛 Troubleshooting

### Problem: All APIs failing

**Check:**
1. Are your API keys correct in `.env`?
2. Have you hit rate limits?
3. Are the APIs down? (Check their status pages)
4. Is Redis connected? (Check logs)

**Solution:**
```bash
# Check API health
curl http://localhost:8000/api/health/api-status

# Check logs
docker-compose logs backend | grep "SportsDataService"

# Reset circuit breakers
curl -X POST http://localhost:8000/api/health/reset-circuit-breakers
```

### Problem: Specific API not working

**Check circuit breaker status:**
```bash
# View API status in browser
http://localhost:8000/docs
# Navigate to GET /api/health/api-status
```

**If circuit is OPEN:**
- Wait 60 seconds for automatic reset
- Or manually reset via endpoint
- Check API key is valid
- Verify you haven't hit rate limits

### Problem: Rate limited

**Symptoms:**
- HTTP 429 errors in logs
- Circuit breaker trips immediately
- "Rate limit exceeded" messages

**Solutions:**
1. **Configure another API** as backup
2. **Increase cache TTL** to reduce API calls:
   ```env
   CACHE_SCORES_SECONDS=120  # Double the cache time
   ```
3. **Upgrade API tier** for higher limits
4. **Use free APIs** (MLB, NHL) that don't have rate limits

### Problem: Stale data being returned

**This is expected behavior!**

When all APIs fail, the app returns cached data (even if expired) rather than showing no data.

**Check:**
```bash
# Look for "Returning stale cache data" in logs
docker-compose logs backend | grep "stale cache"
```

**If you don't want stale data:**
- Fix the API issues
- Ensure at least one API is working
- Check API health endpoint

## 📈 Cost Optimization

### Free Setup

Use only free APIs:
- **The Odds API**: 500 requests/month free
- **MLB Stats API**: Unlimited, free
- **NHL Stats API**: Unlimited, free

**Estimated cost:** $0/month

### Basic Setup

Add ESPN API with low-tier plan:
- **ESPN API**: ~$20/month (estimate)
- **The Odds API**: Free tier
- **Free APIs**: MLB, NHL

**Estimated cost:** ~$20/month

### Production Setup

All APIs with paid tiers:
- **ESPN API**: ~$50-100/month
- **The Odds API**: ~$20/month
- **RapidAPI**: ~$30/month
- **Free APIs**: MLB, NHL

**Estimated cost:** ~$100-150/month

**Optimizations:**
1. **Increase cache times** to reduce API calls
2. **Use free APIs first** for some sports
3. **Monitor usage** via API dashboards
4. **Set rate limits** in the app to prevent over-usage

## 🔐 Security

**Never commit API keys!**

- ✅ Keys go in `backend/.env` (gitignored)
- ❌ Never in `backend/.env.example`
- ✅ Use environment variables in production
- ❌ Never hardcode in source code

**Rotate keys if exposed:**
1. Generate new keys in API dashboards
2. Update `.env`
3. Restart backend: `docker-compose restart backend`

## 📚 API Documentation Links

- **ESPN API**: https://developer.espn.com/docs
- **The Odds API**: https://the-odds-api.com/liveapi/guides/v4/
- **RapidAPI**: https://rapidapi.com/hub
- **MLB Stats API**: https://github.com/toddrob99/MLB-StatsAPI
- **NHL API**: https://gitlab.com/dword4/nhlapi

## ✅ Testing Your Setup

1. **Start the app:**
   ```bash
   docker-compose up
   ```

2. **Check logs for API initialization:**
   ```bash
   docker-compose logs backend | grep "SportsDataService"
   ```

   You should see:
   ```
   SportsDataService: ESPN API client initialized
   SportsDataService: The Odds API client initialized
   SportsDataService: RapidAPI client initialized
   ```

3. **Test API health endpoint:**
   ```bash
   # Login and get token first
   curl http://localhost:8000/api/health/api-status \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

4. **Try fetching data** (via API docs at http://localhost:8000/docs)

## 🎯 Best Practices

1. **Configure multiple APIs** for redundancy
2. **Monitor circuit breakers** regularly
3. **Set appropriate cache times** for your use case
4. **Use free APIs** when available (MLB, NHL)
5. **Track API usage** to avoid unexpected costs
6. **Keep API keys secure** (never commit to git)
7. **Test failover** by temporarily removing an API key
8. **Check logs** for API health issues

---

**Need help?** Check the main README.md or create an issue on GitHub.
