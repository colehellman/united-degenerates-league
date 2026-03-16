#!/bin/bash

# Render start script for backend API

echo "Starting United Degenerates League Backend..."

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI server
echo "Starting FastAPI server on port ${PORT:-8000}..."
if [ "$DISABLE_BACKGROUND_JOBS" = "true" ]; then
    echo "Background jobs DISABLED — expecting separate worker service"
fi
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
