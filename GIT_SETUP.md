# Git Setup - Safe First Commit

Follow these steps to safely initialize your git repository and make your first commit without exposing sensitive information.

## Step 1: Initialize Git Repository

```bash
cd /Users/colehellman/workspace/udl
git init
```

## Step 2: Verify .gitignore is Working

Before adding any files, verify that sensitive files are ignored:

```bash
# Check what files git sees
git status

# Specifically check that .env is ignored
git check-ignore backend/.env

# Should output: backend/.env
# If it doesn't output anything, .gitignore isn't working!
```

## Step 3: Review What Will Be Committed

```bash
# See all files that will be added
git status

# Make sure you DON'T see:
# ❌ backend/.env
# ❌ node_modules/
# ❌ __pycache__/
# ❌ *.pyc files
# ❌ dist/ or build/ folders
```

## Step 4: Safe Files to Commit

You SHOULD see these files:
```
✅ .gitignore
✅ README.md
✅ SECURITY.md
✅ SETUP_GUIDE.md
✅ docker-compose.yml
✅ backend/.env.example (NOT .env)
✅ backend/app/*.py
✅ backend/requirements.txt
✅ backend/alembic/
✅ frontend/src/
✅ frontend/package.json
✅ frontend/tsconfig.json
✅ frontend/vite.config.ts
✅ frontend/tailwind.config.js
```

## Step 5: Add Files to Git

```bash
# Add all files (safe because .gitignore is working)
git add .

# Double-check what's staged
git status

# Review the files to be committed
git diff --cached --name-only
```

## Step 6: Make Your First Commit

```bash
git commit -m "Initial commit - United Degenerates League application

- FastAPI backend with JWT authentication
- React + TypeScript frontend with Tailwind CSS
- PostgreSQL database with SQLAlchemy models
- Docker Compose development environment
- Comprehensive API for sports predictions
- Daily Picks and Fixed Teams modes
- Admin tools and audit logging
"
```

## Step 7: Verify No Secrets Were Committed

```bash
# Search for common secret patterns in committed files
git log --all --full-history --source --all -- "*/.env"
# Should be empty

# Search for hardcoded passwords (should find none in actual values)
git grep -i "password.*=" -- "*.py" "*.ts" "*.tsx"
# Should only find variable names, not actual passwords

# Search for API keys (should find none in actual values)
git grep -i "api_key.*=" -- "*.py" "*.env"
# Should only find references in .env.example
```

## Step 8: Set Up Remote Repository (Optional)

```bash
# Add remote repository (GitHub, GitLab, etc.)
git remote add origin https://github.com/yourusername/udl.git

# Push to remote
git push -u origin main

# Or if using 'master' as default branch
git push -u origin master
```

## Quick Verification Commands

Run these before EVERY push:

```bash
# 1. Check no .env files are tracked
git ls-files | grep ".env$"
# Should be empty (or only show .env.example)

# 2. Check no sensitive files
git status
# Should not show backend/.env, node_modules, etc.

# 3. Check what will be pushed
git diff origin/main --name-only
# Or: git diff origin/master --name-only
```

## Common Git Commands for This Project

### Daily Development

```bash
# See what changed
git status

# Add specific files
git add backend/app/api/auth.py
git add frontend/src/pages/Dashboard.tsx

# Or add all (safe with .gitignore)
git add .

# Commit with message
git commit -m "Add user authentication endpoint"

# Push to remote
git push
```

### Before Committing New Environment Variables

If you add new sensitive config:

```bash
# 1. Add to .gitignore if needed
echo "new_secret_file.txt" >> .gitignore

# 2. Verify it's ignored
git check-ignore new_secret_file.txt

# 3. Add to .env.example with placeholder
echo "NEW_API_KEY=your-api-key-here" >> backend/.env.example

# 4. Commit the example, not the real file
git add backend/.env.example
git commit -m "Add NEW_API_KEY to environment variables"
```

### Undoing Mistakes

```bash
# Unstage a file
git reset HEAD backend/.env

# Remove file from git but keep locally
git rm --cached backend/.env

# Undo last commit (keep changes)
git reset HEAD^

# Undo last commit (discard changes) - DANGEROUS!
git reset --hard HEAD^
```

## Security Checklist Before First Push

- [ ] `.gitignore` file exists and is committed
- [ ] `backend/.env` is NOT in `git status`
- [ ] `backend/.env.example` exists with placeholder values
- [ ] No API keys in code (use environment variables)
- [ ] No passwords in code (use environment variables)
- [ ] `node_modules/` is NOT in `git status`
- [ ] `__pycache__/` is NOT in `git status`
- [ ] SECRET_KEY in .env is strong and unique
- [ ] SECURITY.md document reviewed

## Example: Safe vs Unsafe Files

### ❌ NEVER COMMIT:
```
backend/.env                    # Real secrets
backend/.venv/                  # Python virtual env
frontend/node_modules/          # Dependencies
backend/__pycache__/            # Python cache
*.pyc                          # Compiled Python
.DS_Store                      # Mac OS files
*.log                          # Log files
postgres_data/                 # Database data
```

### ✅ SAFE TO COMMIT:
```
backend/.env.example           # Template with placeholders
backend/app/*.py              # Source code
frontend/src/*.tsx            # Source code
docker-compose.yml            # Uses env variables
requirements.txt              # Dependency list
package.json                  # Dependency list
README.md                     # Documentation
.gitignore                    # Git ignore rules
```

## Need Help?

If you're unsure whether a file is safe to commit:

1. Check if it's in `.gitignore`
2. Look for passwords, API keys, or secrets in the file
3. If in doubt, DON'T commit it
4. Ask in your team chat or review SECURITY.md

---

**Remember**: You can always add files later, but removing secrets from git history is very difficult!
