# Railway Deployment Checklist ✅

## Before You Deploy

### 1. Check Files Exist (ROOT directory)

```bash
cd /Users/colehellman/workspace/udl

# All these should exist:
ls start.sh              # ✅
ls Procfile              # ✅
ls railway.json          # ✅
ls nixpacks.toml         # ✅
ls runtime.txt           # ✅
```

### 2. Check Backend Files

```bash
ls backend/start.sh          # ✅ (backup)
ls backend/requirements.txt  # ✅
ls backend/alembic.ini       # ✅
ls backend/app/main.py       # ✅
```

### 3. Commit to Git

```bash
# Add new files
git add start.sh Procfile railway.json nixpacks.toml runtime.txt

# Make start.sh executable in git
git update-index --chmod=+x start.sh

# Commit
git commit -m "Add Railway deployment files with start.sh in root"

# Push to GitHub
git push origin main
```

## Railway Setup

### 4. Create/Check Railway Project

- [ ] Railway project created at https://railway.app
- [ ] Connected to your GitHub repository
- [ ] Repository access granted

### 5. Add Database Services

In Railway Dashboard:

- [ ] Click "New" → "Database" → "Add PostgreSQL"
- [ ] Click "New" → "Database" → "Add Redis" (recommended)
- [ ] Wait for both to be "Active"

### 6. Configure Backend Service

Click on your backend service:

**Settings Tab:**
- [ ] **DO NOT** set Root Directory (leave it empty for monorepo)
- [ ] Or set to `.` (current directory)

**Variables Tab:**
Add these environment variables:

```env
SECRET_KEY=<generate-strong-random-key>
ENVIRONMENT=production
THE_ODDS_API_KEY=your-api-key-here
```

**Generate SECRET_KEY:**
```bash
# On Mac/Linux:
openssl rand -base64 32

# Or Python:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Networking Tab:**
- [ ] Click "Generate Domain"
- [ ] Copy your URL: `https://your-app-name.railway.app`

## Deployment

### 7. Trigger Deployment

Railway should auto-deploy when you push. If not:

- [ ] Click "Deploy" button (top right)
- [ ] Select "Redeploy"

### 8. Watch Logs

Click on service → Deployments → Latest deployment → View Logs

**Look for:**
```
✅ "United Degenerates League - Starting Backend"
✅ "Running database migrations..."
✅ "Starting FastAPI server..."
✅ "Application startup complete"
```

**Red flags:**
```
❌ "start.sh not found"
❌ "Module not found"
❌ "Database connection failed"
❌ "SECRET_KEY not set"
```

## Post-Deployment Verification

### 9. Test Endpoints

```bash
# Replace YOUR_URL with your Railway domain

# Health check
curl https://YOUR_URL.railway.app/health

# API documentation
open https://YOUR_URL.railway.app/docs
```

### 10. Test Registration

Using the Swagger docs at `/docs`:

1. Open `/api/auth/register` endpoint
2. Click "Try it out"
3. Enter test data:
   ```json
   {
     "email": "test@example.com",
     "username": "testuser",
     "password": "testpassword123"
   }
   ```
4. Click "Execute"
5. Should get 201 response with access token

### 11. Check API Health

```bash
# Get token from registration response, then:
curl https://YOUR_URL.railway.app/api/health/api-status \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Environment Variables Checklist

### Required
- [x] `SECRET_KEY` (set manually)
- [x] `DATABASE_URL` (auto-set by Railway)
- [x] `REDIS_URL` (auto-set by Railway)
- [x] `ENVIRONMENT=production`

### Recommended
- [ ] `THE_ODDS_API_KEY` (at least one Sports API)
- [ ] `ESPN_API_KEY` (for redundancy)
- [ ] `CORS_ORIGINS` (if deploying frontend)

### Optional
- [ ] `RAPIDAPI_KEY`
- [ ] `SPORTSDATA_API_KEY`
- [ ] `CIRCUIT_BREAKER_FAILURE_THRESHOLD=5`
- [ ] `CACHE_SCORES_SECONDS=60`

## Troubleshooting

### If "start.sh not found"

1. Check file is in ROOT directory:
   ```bash
   ls -la start.sh
   ```

2. Check it's committed:
   ```bash
   git log --oneline -1
   git ls-files | grep start.sh
   ```

3. Check it's executable:
   ```bash
   git ls-files --stage start.sh
   # Should be: 100755 (not 100644)
   ```

4. Fix permissions if needed:
   ```bash
   git update-index --chmod=+x start.sh
   git commit -m "Fix start.sh permissions"
   git push
   ```

### If Build Fails

Check Railway logs for specific error, then:

- **"Module not found"** → Check requirements.txt exists in backend/
- **"Can't find alembic"** → Check alembic.ini exists in backend/
- **"Permission denied"** → Make start.sh executable (see above)

### If App Crashes After Build

Check logs for:

- **"SECRET_KEY not set"** → Add to Railway variables
- **"Can't connect to database"** → Add PostgreSQL service
- **"Connection refused"** → Check app is binding to `0.0.0.0:$PORT`

## Success Criteria

✅ Build completes without errors
✅ Migrations run successfully
✅ FastAPI server starts
✅ Service shows "Active" status
✅ `/health` endpoint returns 200
✅ `/docs` page loads
✅ Can register a test user

## Quick Commands Reference

```bash
# Commit and deploy
git add .
git commit -m "Your message"
git push

# View Railway logs (if CLI installed)
railway logs

# Run migrations manually
railway run alembic upgrade head

# SSH into container
railway run bash
```

## Need Help?

1. ✅ Check `RAILWAY_FIX.md` for detailed fix
2. ✅ Check `RAILWAY_QUICKSTART.md` for quick guide
3. ✅ Check `RAILWAY_DEPLOYMENT.md` for comprehensive guide
4. 📞 Railway Discord: https://discord.gg/railway
5. 📚 Railway Docs: https://docs.railway.app/

---

**Current Status:** All Railway files created in ROOT directory ✅

**Next Step:** Commit and push to trigger deployment! 🚀
