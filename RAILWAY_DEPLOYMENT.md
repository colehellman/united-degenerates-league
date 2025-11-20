# Railway Deployment Guide

This guide will walk you through deploying the United Degenerates League to Railway.app.

## 🏗️ Architecture

Railway deployment uses a **multi-service approach**:

1. **PostgreSQL Database** (Railway managed)
2. **Redis Cache** (Railway managed)
3. **Backend API** (FastAPI)
4. **Frontend** (React - Optional, can use Vercel instead)

## 📋 Prerequisites

1. Railway account: https://railway.app
2. GitHub repository with your code
3. Railway CLI (optional): `npm install -g @railway/cli`

## 🚀 Deployment Steps

### Step 1: Create a New Railway Project

1. Go to https://railway.app/new
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account and select the UDL repository

### Step 2: Add PostgreSQL Database

1. In your Railway project, click "New"
2. Select "Database" → "Add PostgreSQL"
3. Railway will automatically provision a PostgreSQL database
4. Note: The `DATABASE_URL` environment variable is automatically set

### Step 3: Add Redis Cache

1. Click "New" again
2. Select "Database" → "Add Redis"
3. Railway will provision Redis
4. Note: The `REDIS_URL` environment variable is automatically set

### Step 4: Deploy Backend Service

#### Option A: Deploy from Root Directory

1. In your Railway project, click "New"
2. Select "GitHub Repo"
3. Choose your repository
4. Railway will detect it's a Python project

**Configure the service:**

1. Click on the service
2. Go to "Settings" tab
3. Set **Root Directory**: `backend`
4. Go to "Variables" tab
5. Add environment variables:

```env
SECRET_KEY=<generate-strong-random-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=production

# CORS - Update with your frontend domain
CORS_ORIGINS=https://your-frontend-domain.railway.app,https://yourdomain.com

# Sports APIs
ESPN_API_KEY=your-espn-key
THE_ODDS_API_KEY=your-odds-api-key
RAPIDAPI_KEY=your-rapidapi-key

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60

# Caching
CACHE_SCORES_SECONDS=60
CACHE_LEADERBOARD_SECONDS=30
CACHE_USER_PREFS_SECONDS=300
```

6. Go to "Settings" → "Networking"
7. Click "Generate Domain" to get a public URL

#### Option B: Deploy with Railway CLI

```bash
# Navigate to backend directory
cd backend

# Login to Railway
railway login

# Initialize project (if not already linked)
railway link

# Add environment variables
railway variables set SECRET_KEY="your-secret-key"
railway variables set ENVIRONMENT="production"
# ... add all other variables

# Deploy
railway up
```

### Step 5: Deploy Frontend (Optional)

**Note:** You can deploy the frontend to Vercel, Netlify, or Railway. Railway instructions:

1. Click "New" in your Railway project
2. Select "GitHub Repo" (same repository)
3. Configure:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Start Command**: `npm run start`

4. Add environment variable:
   ```env
   VITE_API_URL=https://your-backend-url.railway.app
   ```

5. Generate domain for frontend

### Step 6: Run Database Migrations

After backend is deployed:

**Option A: Through Railway Dashboard**

1. Click on backend service
2. Go to "Deployments" tab
3. Click on latest deployment
4. Click "View Logs"
5. The migrations should run automatically via `start.sh`

**Option B: Using Railway CLI**

```bash
# Connect to backend service
railway run alembic upgrade head
```

**Option C: Railway Shell**

1. Go to backend service
2. Click "Settings" → "Shell"
3. Run: `alembic upgrade head`

### Step 7: Verify Deployment

1. **Check Backend Health:**
   ```bash
   curl https://your-backend-url.railway.app/health
   ```

2. **Check API Documentation:**
   Open `https://your-backend-url.railway.app/docs`

3. **Check Database Connection:**
   Look at deployment logs for "Database connected" message

4. **Test Registration:**
   Use the `/api/auth/register` endpoint

## 🔧 Configuration

### Environment Variables Reference

#### Required Variables

```env
# Security (REQUIRED - Generate strong keys!)
SECRET_KEY=<use: openssl rand -base64 32>
DATABASE_URL=<automatically set by Railway>
REDIS_URL=<automatically set by Railway>

# Environment
ENVIRONMENT=production

# CORS (Update with your domains)
CORS_ORIGINS=https://your-frontend.railway.app,https://yourdomain.com
```

#### Recommended Variables

```env
# At least one Sports API
THE_ODDS_API_KEY=your-key

# Token expiration
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### Optional Variables

```env
# Additional Sports APIs
ESPN_API_KEY=your-key
RAPIDAPI_KEY=your-key

# Circuit Breaker tuning
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60

# Cache tuning
CACHE_SCORES_SECONDS=60
CACHE_SCHEDULE_SECONDS=3600
```

### Generate Secure SECRET_KEY

```bash
# Method 1: OpenSSL
openssl rand -base64 32

# Method 2: Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Method 3: Online (use a trusted source)
# https://randomkeygen.com/
```

## 🔍 Troubleshooting

### Issue: Build Fails

**Error:** "Could not determine how to build the app"

**Solution:**
- Ensure `backend/start.sh` exists and is executable
- Check `backend/Procfile` exists
- Verify `backend/requirements.txt` is present
- Set correct Root Directory in Railway settings

### Issue: Database Connection Fails

**Error:** "Could not connect to database"

**Solution:**
- Ensure PostgreSQL service is running
- Check `DATABASE_URL` is set (should be automatic)
- Verify backend service is in same Railway project
- Check Railway network settings

### Issue: Migrations Don't Run

**Error:** "Table does not exist"

**Solution:**
```bash
# Use Railway shell to run migrations manually
railway shell
alembic upgrade head
```

Or check that `start.sh` is being executed (check logs).

### Issue: CORS Errors in Frontend

**Error:** "Access blocked by CORS policy"

**Solution:**
- Update `CORS_ORIGINS` environment variable with frontend domain
- Format: `https://frontend.railway.app,https://yourdomain.com`
- Restart backend service after changing

### Issue: Redis Connection Fails

**Error:** "Could not connect to Redis"

**Solution:**
- Ensure Redis service is running in Railway project
- Check `REDIS_URL` environment variable is set
- Redis is optional - app will work without cache (slower)

### Issue: API Keys Not Working

**Error:** "Rate limit exceeded" or "Invalid API key"

**Solution:**
- Verify API keys are correctly set in Railway variables
- No quotes around values in Railway dashboard
- Check API key validity in provider dashboards
- Use at least 2 APIs for redundancy

## 📊 Monitoring

### View Logs

1. Go to service in Railway dashboard
2. Click "Deployments"
3. Click on a deployment
4. View real-time logs

### Check Metrics

1. Go to service
2. Click "Metrics" tab
3. View CPU, Memory, Network usage

### Set Up Alerts

1. Go to project settings
2. Set up webhooks for deployment failures
3. Configure Discord/Slack notifications

## 🔄 Continuous Deployment

Railway automatically deploys when you push to your GitHub repository.

**To disable auto-deploy:**
1. Go to service settings
2. Scroll to "Source"
3. Toggle "Auto-deploy" off

**To manually deploy:**
1. Click "Deploy" button in dashboard
2. Or use CLI: `railway up`

## 💰 Cost Estimation

Railway pricing (as of 2024):

- **Hobby Plan**: $5/month
  - Includes $5 credit
  - Pay for usage above credit

- **Typical Monthly Cost:**
  - PostgreSQL: ~$2-5
  - Redis: ~$1-2
  - Backend: ~$2-5
  - Frontend: ~$1-2
  - **Total: ~$6-14/month**

**Cost Optimization Tips:**
1. Use sleep mode for non-production environments
2. Optimize API calls (use caching)
3. Use frontend on Vercel (free tier)
4. Monitor usage in Railway dashboard

## 🚦 Production Checklist

Before going live:

- [ ] Strong `SECRET_KEY` generated and set
- [ ] `ENVIRONMENT=production` set
- [ ] Database backups configured
- [ ] CORS origins properly configured
- [ ] At least 2 Sports APIs configured
- [ ] SSL/HTTPS enabled (automatic on Railway)
- [ ] Custom domain connected (optional)
- [ ] Monitoring and alerts set up
- [ ] Rate limiting configured
- [ ] Error tracking set up (Sentry, etc.)

## 🔗 Useful Links

- **Railway Dashboard**: https://railway.app/dashboard
- **Railway Docs**: https://docs.railway.app/
- **Railway Discord**: https://discord.gg/railway
- **Railway Status**: https://status.railway.app/

## 📞 Support

If you encounter issues:

1. Check Railway logs first
2. Review this guide's troubleshooting section
3. Check Railway Discord for help
4. Open an issue on GitHub

## 🎯 Alternative: Deploy Frontend to Vercel

For better performance, deploy frontend separately:

1. Go to https://vercel.com
2. Import your GitHub repository
3. Set Root Directory: `frontend`
4. Set Environment Variable:
   ```env
   VITE_API_URL=https://your-backend.railway.app
   ```
5. Deploy

Vercel provides:
- Global CDN
- Automatic HTTPS
- Free for hobby projects
- Better frontend performance

---

**You're all set!** Your app is now deployed to Railway with PostgreSQL, Redis, and automatic deployments. 🚀
