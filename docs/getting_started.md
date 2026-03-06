# Getting Started

This guide provides instructions on how to set up and run the application locally for development.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Git
- Docker (Recommended for running PostgreSQL and Redis)

## 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

## 2. Backend Setup

### Install Python Dependencies

```bash
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Environment Variables

```bash
# Create .env file from example
cp .env.example .env

# Edit .env with your settings
# The default values should work for local development.
nano .env  # or use your preferred editor
```

### Start PostgreSQL and Redis using Docker

The recommended way to run PostgreSQL and Redis is by using the provided `docker-compose.yml` file.

```bash
# From the project root
docker-compose up -d postgres redis

# Verify they're running
docker-compose ps
```

### Run Database Migrations

```bash
# From the backend directory
cd backend

# Run migrations
alembic upgrade head
```

### Seed Database with Sample Data

```bash
# Still in backend directory
python3 -m scripts.seed_data
```

### Start Backend Server

```bash
# From the backend directory
uvicorn app.main:app --reload
```

Verify the backend is running by opening your browser to: [http://localhost:8000/docs](http://localhost:8000/docs). You should see the FastAPI Swagger documentation.

## 3. Frontend Setup

Open a new terminal window/tab.

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Verify the frontend is running by opening your browser to: [http://localhost:5173](http://localhost:5173). You should see the application's login page.

## 4. Common Issues & Fixes

### Issue: "ModuleNotFoundError: No module named 'sqlalchemy'"

**Fix:** Install backend dependencies.
```bash
cd backend
pip install -r requirements.txt
```

### Issue: "alembic.util.exc.CommandError: Can't locate revision identified by"

**Fix:** The database is in an inconsistent state.
```bash
# Drop and recreate database
# If using docker-compose, you can stop and remove the volume
docker-compose down -v
docker-compose up -d postgres redis

# Run migrations again
cd backend
alembic upgrade head
```

### Issue: "Connection refused" when starting backend

**Fix:** PostgreSQL or Redis are not running.
```bash
# Check if services are running
docker-compose ps
```

### Issue: Frontend shows "Network Error"

**Fix:** The backend is not running or the frontend is configured with the wrong URL.
```bash
# Verify backend is running on http://localhost:8000
curl http://localhost:8000/api/health

# Check the frontend .env file. It should contain:
# VITE_API_URL=http://localhost:8000
```
