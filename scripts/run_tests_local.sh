#!/bin/bash
# Run tests with .env.local explicitly loaded
# Usage: ./scripts/run_tests_local.sh [pytest args]

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

# Run pytest with all arguments passed to this script
echo "Running tests..."
python -m pytest "$@"

