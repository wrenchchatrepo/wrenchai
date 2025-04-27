# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core /app/core
COPY fastapi /app/fastapi
COPY alembic.ini .
COPY migrations /app/migrations

# Create and switch to non-root user
RUN useradd -m -s /bin/bash app && \
    chown -R app:app /app
USER app

# Expose FastAPI port
EXPOSE 8000

# Set health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start FastAPI with Uvicorn
CMD ["uvicorn", "fastapi.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"] 