# Dockerfile for Stock Portfolio Analyzer
# Optimized for OMV Docker Compose deployment

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - gcc / build-essential: needed for some Python packages (numpy, pandas)
# - curl: needed for Docker healthcheck
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    libc6-dev \
    python3-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create the data directory for SQLite DB persistence via volume mount
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Environment variable defaults
ENV PORT=8000 \
    DATA_DIR=/data \
    DEBUG=false

# Run with Gunicorn (2 workers is fine for home server; increase if needed)
CMD gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    wsgi:application
