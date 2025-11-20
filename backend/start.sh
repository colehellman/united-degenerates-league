#!/bin/bash

# Railway start script for backend

echo "Starting United Degenerates League Backend..."

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI server
echo "Starting FastAPI server on port $PORT..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
