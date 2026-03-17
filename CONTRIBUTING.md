# Contributing to United Degenerates League

## Getting Started

### Prerequisites

- Python 3.11
- Node.js 20+
- Docker & Docker Compose (recommended)
- PostgreSQL 15 and Redis 7 (if running without Docker)

### Setup

```bash
# Clone the repo
git clone https://github.com/colehellman/united-degenerates-league.git
cd united-degenerates-league

# Option 1: Docker (recommended)
docker-compose up --build
docker-compose exec backend alembic upgrade head

# Option 2: Manual
# Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:3000 (frontend) and http://localhost:8000 (backend).

## Development Workflow

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/<short-description>` | `feat/dark-mode` |
| Bug fix | `fix/<short-description>` | `fix/pick-locking-race` |
| Refactor | `refactor/<short-description>` | `refactor/auth-middleware` |
| Docs | `docs/<short-description>` | `docs/api-examples` |

### Making Changes

1. Create a branch from `main`
2. Make your changes
3. Run linting and tests locally before pushing
4. Open a PR against `main`

### Running Tests

```bash
# Backend (requires Postgres + Redis running)
cd backend && source .venv/bin/activate
pytest tests/ -v --tb=short

# Frontend unit tests
cd frontend && npm test

# Frontend E2E tests (requires full stack running)
cd frontend && npx playwright test

# Backend linting
cd backend && ruff check app/ tests/ worker.py
cd backend && ruff format --check app/ tests/ worker.py

# Frontend linting
cd frontend && npm run lint
```

### Pre-commit Hooks

This project uses pre-commit hooks to catch issues before they reach CI:

```bash
pip install pre-commit
pre-commit install
```

Hooks run automatically on `git commit`. To run manually:

```bash
pre-commit run --all-files
```

## Code Conventions

### Python (Backend)

- **Style**: snake_case functions, PascalCase classes
- **Type hints**: Required on all public functions
- **Imports**: stdlib, third-party, local (3-group, enforced by ruff/isort)
- **Models**: UUID primary keys, `created_at`/`updated_at` timestamps
- **API**: Pydantic schemas for all request/response bodies
- **Linter**: ruff (see `backend/ruff.toml` for rule configuration)

### TypeScript (Frontend)

- **Components/Pages**: PascalCase
- **Services/Hooks**: camelCase
- **Types**: Prefer `interface` over `type`
- **State**: Zustand for auth, TanStack Query for server state

### Database

- Always create an Alembic migration for schema changes:
  ```bash
  cd backend && alembic revision --autogenerate -m "description"
  ```
- Use UUID primary keys on all models
- Add `relationship()` with `back_populates` for bidirectional relations

### Git

- Write commit messages that explain **why**, not just what
- Keep PRs focused — one feature or fix per PR
- Squash-merge is preferred for feature branches

## CI Pipeline

Every PR runs:

| Check | What it does |
|-------|-------------|
| **backend-test** | pytest with Postgres + Redis |
| **frontend-build** | TypeScript check, Vite build, Vitest |
| **e2e** | Playwright tests against full stack |
| **sync-docs** | Auto-updates documentation markers |
| **ruff** | Python linting and format checking |

All checks must pass before merging.

## Architecture

See [docs/architecture.md](docs/architecture.md) for a full system architecture diagram and design decisions.

## Questions?

Open an issue or check the existing documentation in `CLAUDE.md` for detailed project notes.
