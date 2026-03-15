# Security Checklist

## 🔒 Sensitive Files - NEVER Commit These!

### ✅ Before Your First Commit

1. **Verify .gitignore is working:**
   ```bash
   git status
   # Should NOT show .env files, node_modules, __pycache__, etc.
   ```

2. **Check what's staged:**
   ```bash
   git add -A
   git status
   # Review carefully - should only see code files, not secrets
   ```

3. **Remove sensitive files from git history if accidentally committed:**
   ```bash
   # If you accidentally committed .env
   git rm --cached backend/.env
   git commit -m "Remove .env from tracking"
   ```

## 🚨 Critical Files to Protect

### Backend
- ❌ `backend/.env` - Contains database passwords, API keys, SECRET_KEY
- ✅ `backend/.env.example` - Safe to commit (no real values)
- ❌ Any file with actual API keys or passwords
- ❌ `__pycache__/` directories
- ❌ `*.pyc` files

### Frontend
- ❌ `frontend/.env.local` - May contain API URLs or keys
- ❌ `node_modules/` - Huge dependency folder
- ❌ `frontend/dist/` - Built files

### Database
- ❌ `*.db`, `*.sqlite` - Local database files
- ❌ Database dump files (`*.dump`, `*.sql.backup`)
- ❌ Docker volume data (`postgres_data/`)

### Docker
- ❌ `docker-compose.override.yml` - May contain local configs
- ✅ `docker-compose.yml` - Safe to commit (uses env variables)

## 🔑 Environment Variables to Protect

Never commit files containing:
- `SECRET_KEY` - Used for JWT token signing
- `DATABASE_URL` - Contains database password
- `ESPN_API_KEY`, `THE_ODDS_API_KEY`, `RAPIDAPI_KEY`, etc. - Sports API credentials
- Any password or authentication token

## ✅ Safe to Commit

- Source code (`.py`, `.tsx`, `.ts` files)
- Configuration templates (`.env.example`)
- Documentation (`.md` files)
- Docker configuration (`docker-compose.yml` that uses env vars)
- Database migrations (`alembic/versions/*.py`)
- Package definitions (`requirements.txt`, `package.json`)

## 🛡️ Production Security Checklist

Before deploying to production:

### 1. Environment Variables
- [ ] Generate strong SECRET_KEY (32+ random characters)
- [ ] Use production database credentials
- [ ] Set ENVIRONMENT=production
- [ ] Update CORS_ORIGINS to production domains only
- [ ] Verify all API keys are production keys

### 2. Database Security
- [ ] Use strong database password
- [ ] Enable SSL for database connections
- [ ] Restrict database access to application servers only
- [ ] Regular backups configured
- [ ] Connection limits set

### 3. API Security
- [ ] Rate limiting enabled and tested
- [ ] HTTPS enforced (redirect HTTP to HTTPS)
- [ ] CORS properly configured
- [ ] No debug endpoints exposed
- [ ] API documentation disabled or password-protected

### 4. Docker Security
- [ ] Don't run containers as root
- [ ] Use specific image versions (not `latest`)
- [ ] Scan images for vulnerabilities
- [ ] Limit container resources
- [ ] Use Docker secrets for sensitive data

### 5. Application Security
- [ ] JWT tokens have reasonable expiration times
- [ ] Password requirements enforced (min 8 chars)
- [ ] SQL injection prevention verified
- [ ] XSS protection enabled
- [ ] CSRF protection configured
- [ ] Sensitive data encrypted at rest

## 🔐 Generating Secure Secrets

### SECRET_KEY for JWT
```python
# In Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```bash
# In terminal
openssl rand -base64 32
```

### Database Password
```bash
# Generate 20-character random password
openssl rand -base64 20
```

## 📋 Pre-Deployment Checklist

```bash
# 1. Check for secrets in code
grep -r "SECRET_KEY\|password\|api_key" backend/app/ frontend/src/
# Should find NO hardcoded values!

# 2. Check git status
git status
# Should NOT show .env files

# 3. Search git history for secrets (if paranoid)
git log --all --full-history -- "*/.env"
# Should be empty

# 4. Verify .gitignore is working
git check-ignore backend/.env
# Should output: backend/.env

# 5. Test with production-like settings locally
ENVIRONMENT=production docker-compose up
```

## 🚨 If Secrets Are Exposed

If you accidentally commit secrets to git:

### 1. Immediate Actions
```bash
# Remove from current commit
git reset HEAD^ backend/.env
git commit --amend

# Or remove from tracking but keep local file
git rm --cached backend/.env
git commit -m "Remove .env from tracking"
```

### 2. Rotate ALL Exposed Secrets
- Generate new SECRET_KEY
- Change database password
- Rotate all API keys
- Update production environment variables

### 3. Clean Git History (if already pushed)
```bash
# Use BFG Repo-Cleaner or git filter-branch
# WARNING: This rewrites history!
bfg --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

### 4. If Pushed to Public Repository
- Assume all secrets are compromised
- Rotate EVERYTHING immediately
- Consider the repository permanently tainted
- May need to create new repository

## 📞 Security Contact

For security issues, contact: [your-security-email@domain.com]

---

**Remember**: When in doubt, don't commit it! You can always add files later, but removing secrets from git history is painful.
