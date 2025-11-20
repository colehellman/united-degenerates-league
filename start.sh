#!/bin/bash

# Railway start script for United Degenerates League Backend
# This file must be in the ROOT directory for Railway to find it

echo "================================================"
echo "United Degenerates League - Starting Backend"
echo "================================================"

# Navigate to backend directory
cd backend

echo "Current directory: $(pwd)"
echo "Contents:"
ls -la

# Check if requirements are installed
echo ""
echo "Checking Python dependencies..."
pip list | grep fastapi

# Run database migrations
echo ""
echo "Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✓ Migrations completed successfully"
else
    echo "✗ Migration failed, but continuing..."
fi

# Start the FastAPI server
echo ""
echo "Starting FastAPI server on port $PORT..."
echo "================================================"

# Use Railway's PORT environment variable, default to 8000
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
