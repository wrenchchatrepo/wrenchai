#!/bin/bash
set -e

# Function to log messages with timestamps
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to wait for a service to be ready
wait_for_service() {
    echo "Waiting for $1..."
    python scripts/wait_for_db.py
    if [ $? -ne 0 ]; then
        echo "Error: $1 not available"
        exit 1
    fi
}

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."
    python scripts/init_db.py
    if [ $? -ne 0 ]; then
        echo "Error: Database migrations failed"
        exit 1
    fi
}

# Main startup logic
case "$SERVICE_NAME" in
    "api")
        # Wait for required services
        wait_for_service "database and Redis"
        
        # Run migrations (only for API service)
        run_migrations
        
        # Wait for database to be ready
        log "Waiting for database to be ready..."
        python scripts/wait_for_db.py
        
        # Run database migrations
        log "Running database migrations..."
        alembic upgrade head
        
        # Start FastAPI application
        log "Starting FastAPI application..."
        exec uvicorn core.api:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info
        ;;
        
    "streamlit")
        # Wait for API to be ready
        echo "Waiting for API service..."
        until curl -f http://api:8000/api/health; do
            echo "API is unavailable - sleeping"
            sleep 1
        done
        
        # Start Streamlit application
        echo "Starting Streamlit application..."
        exec streamlit run streamlit_app/app.py \
            --server.port=8501 \
            --server.address=0.0.0.0 \
            --server.baseUrlPath="" \
            --browser.serverAddress="localhost" \
            --browser.gatherUsageStats=false
        ;;
        
    *)
        echo "Error: Unknown service name: $SERVICE_NAME"
        exit 1
        ;;
esac 