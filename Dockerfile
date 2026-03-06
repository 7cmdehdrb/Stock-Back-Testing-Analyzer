# Dockerfile for Stock Analyzer
# Python 3.13.7

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed (e.g. for sqlite3 or gcc)
# Slim image usually suffices for pure python, but adding basics is good practice
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    libc6-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (optional, but good for documentation)
EXPOSE 8000

# Set environment variable defaults
ENV PORT=8000

# Run the application with Gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 wsgi:application
