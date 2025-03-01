#!/bin/bash

# Set environment variables
export PORT=8080
export ENVIRONMENT=production

# Activate virtual environment if it exists
if [ -d "myenv" ]; then
  echo "Activating virtual environment..."
  source myenv/bin/activate
fi

# Install dependencies if needed
if [ "$1" = "--install" ]; then
  echo "Installing dependencies..."
  pip install -r requirements.txt
fi

# Start the server with optimized settings for production
echo "Starting Varanasi Chatbot API server..."
uvicorn app:app \
  --host 0.0.0.0 \
  --port $PORT \
  --workers 4 \
  --timeout-keep-alive 120 \
  --limit-concurrency 20 \
  --timeout-graceful-shutdown 30

# This script can be run with:
# ./start-server.sh
# or to install dependencies:
# ./start-server.sh --install