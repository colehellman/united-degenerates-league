FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for running the application
RUN adduser --disabled-password --gecos "" --uid 1001 appuser

# Copy application code
COPY . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run migrations then start the server
CMD ["bash", "start.sh"]
