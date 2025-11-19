# Quick Setup Guide - United Degenerates League

## Prerequisites
- Docker and Docker Compose installed
- Git (to clone the repository)

## Step-by-Step Setup

### 1. Start the Application

```bash
# From the project root directory
docker-compose up --build
```

This command will:
- Build the backend and frontend Docker images
- Start PostgreSQL database
- Start Redis cache
- Start the backend API server
- Start the frontend development server

Wait for all services to start (you'll see logs from all services).

### 2. Initialize the Database

In a **new terminal window**, run:

```bash
# Create the initial database migration
docker-compose exec backend alembic revision --autogenerate -m "Initial migration"

# Run the migration to create all tables
docker-compose exec backend alembic upgrade head
```

### 3. Access the Application

- **Frontend**: Open http://localhost:3000 in your browser
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)

### 4. Create Your First Account

1. Click "Sign up" on the login page
2. Enter your email, username, and password
3. You'll be automatically logged in and redirected to the dashboard

### 5. Explore the Application

- **Dashboard**: View your active and upcoming competitions
- **Browse Competitions**: See all available competitions
- **Create Competition**: Create your own competition (coming soon - use API docs for now)

## Using the API Documentation

FastAPI provides automatic interactive API documentation at http://localhost:8000/docs

You can:
1. View all available endpoints
2. Test endpoints directly in the browser
3. See request/response schemas
4. Get authentication tokens

### Testing the API

1. Go to http://localhost:8000/docs
2. Click "POST /api/auth/register" to expand
3. Click "Try it out"
4. Fill in the request body:
   ```json
   {
     "email": "test@example.com",
     "username": "testuser",
     "password": "testpassword123"
   }
   ```
5. Click "Execute"
6. Copy the `access_token` from the response
7. Click the "Authorize" button at the top
8. Paste the token in the format: `Bearer YOUR_TOKEN_HERE`
9. Now you can test authenticated endpoints!

## Common Issues

### Port Already in Use

If you see errors like "port 5432 is already in use":

```bash
# Stop any existing services
docker-compose down

# Check what's using the port
lsof -i :5432  # or :8000, :3000, :6379

# Kill the process or change the port in docker-compose.yml
```

### Database Connection Errors

```bash
# Restart the services
docker-compose restart

# Check PostgreSQL logs
docker-compose logs postgres

# Verify the database is running
docker-compose ps
```

### Frontend Can't Connect to Backend

1. Check that backend is running: `docker-compose logs backend`
2. Verify CORS settings in `backend/.env`
3. Check `VITE_API_URL` in frontend (should be http://localhost:8000)

### Reset Everything

To start fresh:

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Rebuild and start
docker-compose up --build

# Re-run migrations
docker-compose exec backend alembic upgrade head
```

## Development Workflow

### Backend Changes

The backend has hot-reload enabled. Just edit files in `backend/app/` and the server will restart automatically.

### Frontend Changes

The frontend also has hot-reload. Edit files in `frontend/src/` and changes will appear immediately in your browser.

### Database Schema Changes

When you modify models in `backend/app/models/`:

```bash
# Create a new migration
docker-compose exec backend alembic revision --autogenerate -m "Description of changes"

# Apply the migration
docker-compose exec backend alembic upgrade head
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

## Next Steps

### Add Sports API Keys

1. Obtain API keys from sports data providers (ESPN, SportsData.io, etc.)
2. Edit `backend/.env`:
   ```env
   ESPN_API_KEY=your-api-key-here
   SPORTSDATA_API_KEY=your-api-key-here
   # etc.
   ```
3. Restart the backend: `docker-compose restart backend`

### Implement Sports Data Integration

The backend has placeholder functions in `backend/app/services/background_jobs.py` for:
- Fetching game schedules
- Updating scores
- Locking picks

You'll need to implement these functions to integrate with real sports APIs.

### Create Sample Data

You can use the API to create sample data:
1. Use `/docs` to authenticate
2. Create leagues (manually insert into database for now)
3. Create competitions
4. Have users join competitions

## Production Deployment

See the main README.md for production deployment instructions.

## Getting Help

- Check the main README.md for comprehensive documentation
- View API docs at http://localhost:8000/docs
- Review the specification document for detailed requirements
- Check Docker logs for error messages

---

**You're all set!** Start competing with your friends! 🏆
