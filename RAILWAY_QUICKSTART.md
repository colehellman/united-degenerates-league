# Railway Quick Start - 5 Minutes

## 🚀 Super Quick Deploy

### 1. Create Railway Project

Go to https://railway.app/new → "Deploy from GitHub repo"

### 2. Set Root Directory

**IMPORTANT:** In Railway dashboard for your service:

1. Click on the service (Python app)
2. Go to **Settings** tab
3. Scroll to **Source**
4. Set **Root Directory** to: `backend`
5. Click "Save"

### 3. Add Database & Redis

In your Railway project:

1. Click **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Click **"New"** → **"Database"** → **"Add Redis"**

Railway automatically connects them! ✨

### 4. Add Required Environment Variables

Click on your backend service → **Variables** tab → Add these:

```env
SECRET_KEY=<click "Generate" or use: openssl rand -base64 32>
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend-url.railway.app
THE_ODDS_API_KEY=your-api-key-here
```

**That's it!** Railway will automatically:
- ✅ Detect Python project
- ✅ Install dependencies from requirements.txt
- ✅ Run start.sh
- ✅ Execute database migrations
- ✅ Start FastAPI server

### 5. Get Your Backend URL

1. In backend service, go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Copy the URL: `https://your-app-name.railway.app`

### 6. Test Your API

Visit: `https://your-app-name.railway.app/docs`

You should see the Swagger API documentation! 🎉

## 🔧 Essential Settings

### Minimum Required Environment Variables

```env
# Generate this! Use: openssl rand -base64 32
SECRET_KEY=super-secret-random-string-here

# Tell app it's production
ENVIRONMENT=production

# At least one Sports API (has free tier)
THE_ODDS_API_KEY=your-key-from-the-odds-api.com
```

### Recommended Environment Variables

```env
# Update after you deploy frontend
CORS_ORIGINS=https://your-frontend.railway.app,https://yourdomain.com

# Additional Sports APIs for redundancy
ESPN_API_KEY=your-espn-key
RAPIDAPI_KEY=your-rapidapi-key
```

## 🐛 Common Issues

### "Could not determine how to build"

**Fix:** Set **Root Directory** to `backend` in Settings → Source

### Build succeeds but app crashes

**Fix:** Check logs. Probably missing environment variables:
- `SECRET_KEY` is required
- Database connection (should be automatic)

### Database connection errors

**Fix:**
1. Ensure PostgreSQL service is in the same project
2. Railway auto-sets `DATABASE_URL` - don't manually set it
3. Check the Services tab to see if Postgres is running

### "Module not found" errors

**Fix:** Railway might not be in the right directory
1. Verify Root Directory is set to `backend`
2. Check `requirements.txt` exists in backend folder

## 📱 Deploy Frontend (Optional)

### Option 1: Railway

1. Click "New" in Railway project
2. Select same GitHub repo
3. Set **Root Directory** to `frontend`
4. Add variable: `VITE_API_URL=https://your-backend.railway.app`
5. Generate domain

### Option 2: Vercel (Recommended - Free + Fast)

1. Go to https://vercel.com
2. Import GitHub repo
3. Set Root Directory: `frontend`
4. Add Environment Variable: `VITE_API_URL=https://your-backend.railway.app`
5. Deploy

Vercel is faster for frontend (global CDN) and has generous free tier.

## 💡 Pro Tips

1. **Use Railway CLI** for faster development:
   ```bash
   npm install -g @railway/cli
   railway login
   railway link
   railway logs  # View real-time logs
   ```

2. **View Logs:**
   Dashboard → Service → Deployments → Click deployment → View Logs

3. **Run Commands:**
   Dashboard → Service → Settings → Shell
   ```bash
   # Run migrations manually if needed
   alembic upgrade head
   ```

4. **Auto-deploys:**
   Railway automatically deploys when you push to GitHub
   (Disable in Settings → Source if you want manual deploys)

## 📋 Deployment Checklist

Before you share your app:

- [ ] `SECRET_KEY` set (strong random value)
- [ ] PostgreSQL database added
- [ ] Redis cache added (optional but recommended)
- [ ] At least one Sports API key configured
- [ ] `ENVIRONMENT=production` set
- [ ] Backend domain generated
- [ ] API docs accessible at `/docs`
- [ ] Test user registration works
- [ ] CORS configured if using separate frontend

## 🎯 Expected Project Structure in Railway

```
Your Railway Project
├── Backend Service (Python)
│   ├── Root Directory: backend
│   ├── Start Command: sh start.sh
│   └── Environment: production
├── PostgreSQL Database
│   └── Automatically linked via DATABASE_URL
└── Redis Cache
    └── Automatically linked via REDIS_URL
```

## 🔗 Next Steps

1. ✅ Backend deployed? → Test `/docs` endpoint
2. ✅ Database working? → Try registering a user
3. ✅ APIs configured? → Check `/api/health/api-status`
4. 📱 Deploy frontend → See RAILWAY_DEPLOYMENT.md
5. 🎨 Configure custom domain → Railway Settings → Domains

## 📞 Need Help?

- **Full Guide:** See `RAILWAY_DEPLOYMENT.md`
- **Railway Docs:** https://docs.railway.app/
- **Discord:** https://discord.gg/railway

---

**Total Time:** ~5 minutes from start to deployed backend! 🚀
