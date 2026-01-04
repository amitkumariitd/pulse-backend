#!/bin/bash
# Run the application locally with .env.local explicitly loaded
# Usage: ./scripts/run_local.sh [uvicorn args]

set -e

# Load .env.local if it exists
if [ -f .env.local ]; then
    echo "Loading environment from .env.local..."
    set -a  # automatically export all variables
    source .env.local
    set +a
else
    echo "Warning: .env.local not found"
    exit 1
fi

# Run uvicorn with all arguments passed to this script
echo "Starting application..."
uvicorn main:app --reload --port 8000 "$@"

