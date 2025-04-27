#!/bin/bash

set -e

# Function to log messages with timestamps
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Start the Streamlit application
log "Starting Streamlit application..."
exec streamlit run streamlit_app/app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --browser.serverAddress=0.0.0.0 \
    --server.maxUploadSize=200 