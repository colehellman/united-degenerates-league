FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

# Install Python dependencies
RUN cd backend && pip install --no-cache-dir -r requirements.txt

# Make start.sh executable
RUN chmod +x start.sh

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Run the startup script
CMD ["sh", "start.sh"]
