# Railway Deployment Fix - start.sh Not Found

## ✅ Problem Fixed!

I've created all the necessary files in the **ROOT directory** where Railway expects them.

## 📁 New Files Created (ROOT Directory)

```
udl/  (root)
├── start.sh              ✅ Main startup script (ROOT)
├── Procfile             ✅ Process definition (ROOT)
├── railway.json         ✅ Railway configuration (ROOT)
├── nixpacks.toml        ✅ Build configuration (ROOT)
└── runtime.txt          ✅ Python version specification (ROOT)
```

## 🚀 Deploy Now - Step by Step

### Step 1: Commit and Push Files

```bash
# Check what files are new
git status

# Add all Railway files
git add start.sh Procfile railway.json nixpacks.toml runtime.txt

# Commit
git commit -m "Add Railway deployment configuration files"

# Push to GitHub
git push origin main
# or: git push origin master
```

### Step 2: Railway Will Auto-Deploy

If you already have the Railway project connected:
- Railway will automatically detect the push
- It will start a new deployment
- This time it WILL find `start.sh` ✅

### Step 3: Watch the Build

1. Go to Railway Dashboard
2. Click on your service
3. Go to "Deployments" tab
4. Click on the latest deployment
5. Watch the logs

**You should see:**
```
================================================
United Degenerates League - Starting Backend
================================================
Current directory: /app/backend
Running database migrations...
✓ Migrations completed successfully
Starting FastAPI server on port 8000...
```

## 🔧 Alternative: Manual Trigger

If Railway doesn't auto-deploy:

1. Go to Railway Dashboard
2. Click on your service
3. Click "Deploy" button (top right)
4. Select "Redeploy"

## ⚙️ Railway Configuration Summary

### What `start.sh` Does (ROOT → backend)

```bash
1. Navigate to backend/ directory
2. Run alembic upgrade head (database migrations)
3. Start uvicorn on Railway's $PORT
```

### What `Procfile` Does

```
web: sh start.sh
```
Tells Railway to execute start.sh for the web process.

### What `railway.json` Does

```json
{
  "build": {
    "buildCommand": "cd backend && pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "sh start.sh"
  }
}
```

Tells Railway how to build and start your app.

## 🔍 Verify Everything is Ready

Before pushing, check these files exist:

```bash
# In your root directory
ls -la start.sh        # Should exist ✅
ls -la Procfile        # Should exist ✅
ls -la railway.json    # Should exist ✅
ls -la nixpacks.toml   # Should exist ✅
ls -la runtime.txt     # Should exist ✅

# start.sh should be executable
ls -la start.sh | grep "x"  # Should show execute permissions
```

## 🎯 Required Environment Variables

Make sure these are set in Railway (Service → Variables):

```env
# REQUIRED
SECRET_KEY=<generate-with: openssl rand -base64 32>
ENVIRONMENT=production

# Database & Redis (Auto-set by Railway)
DATABASE_URL=<automatically-set>
REDIS_URL=<automatically-set>

# At least one Sports API
THE_ODDS_API_KEY=your-api-key-here

# Optional but recommended
ESPN_API_KEY=your-espn-key
RAPIDAPI_KEY=your-rapidapi-key
CORS_ORIGINS=https://your-frontend-url.railway.app
```

## 📊 Expected Build Output

When Railway builds your app, you should see:

```
╔══════════════════════════════════════════════════╗
║ Nixpacks v1.x.x                                  ║
╚══════════════════════════════════════════════════╝
────────────────────────────────────────────────────

──> Setting up Python environment
──> Installing dependencies from requirements.txt
──> Successfully installed fastapi uvicorn sqlalchemy...
──> Build complete

──> Starting deployment
──> Running: sh start.sh
================================================
United Degenerates League - Starting Backend
================================================
Running database migrations...
✓ Migrations completed successfully
Starting FastAPI server...
Application startup complete
```

## 🐛 Troubleshooting

### Still Getting "start.sh not found"?

**Check:**
1. ✅ Did you commit and push the file?
   ```bash
   git log --oneline -1  # Should show your commit
   ```

2. ✅ Is it in the ROOT directory (not backend/)?
   ```bash
   ls start.sh  # Should show the file
   ```

3. ✅ Is it executable?
   ```bash
   git ls-files --stage start.sh
   # Should show: 100755 (executable) not 100644
   ```

   If not executable in git:
   ```bash
   git update-index --chmod=+x start.sh
   git commit -m "Make start.sh executable"
   git push
   ```

### Build succeeds but app crashes?

**Check logs for:**
- Missing environment variables (SECRET_KEY)
- Database connection errors (add PostgreSQL service)
- Redis connection errors (add Redis service - optional)

**View logs:**
Railway Dashboard → Service → Deployments → Click deployment → View Logs

### Database migration errors?

**Manual migration:**
1. Railway Dashboard → Service → Settings → Shell
2. Run:
   ```bash
   cd backend
   alembic upgrade head
   ```

## ✅ Success Indicators

You'll know it worked when:

1. ✅ Build completes without errors
2. ✅ You see "Starting FastAPI server..." in logs
3. ✅ Service status shows "Active" (green)
4. ✅ You can access: `https://your-app.railway.app/health`
5. ✅ API docs work: `https://your-app.railway.app/docs`

## 🎉 Next Steps After Successful Deploy

1. **Test API Documentation:**
   ```
   https://your-app.railway.app/docs
   ```

2. **Create Test User:**
   Use the `/api/auth/register` endpoint

3. **Check API Health:**
   ```bash
   curl https://your-app.railway.app/api/health/api-status
   ```

4. **Deploy Frontend:**
   - Option 1: Railway (set Root Directory: `frontend`)
   - Option 2: Vercel (recommended for better performance)

## 📞 Still Having Issues?

1. **Check Railway logs** (most informative!)
2. **Verify all files are committed:**
   ```bash
   git ls-files | grep -E "(start\.sh|Procfile|railway)"
   ```

3. **Check Railway Discord:** https://discord.gg/railway

4. **Share your logs** if asking for help

---

**The fix is in place!** Commit, push, and Railway will deploy successfully. 🚀
