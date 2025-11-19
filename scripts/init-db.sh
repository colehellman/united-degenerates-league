#!/bin/bash

# Script to initialize the database and run migrations

echo "Waiting for PostgreSQL to be ready..."
sleep 5

echo "Creating initial migration..."
cd /app
alembic revision --autogenerate -m "Initial migration - create all tables"

echo "Running migrations..."
alembic upgrade head

echo "Database initialization complete!"
