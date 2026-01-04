#!/bin/bash
set -e

echo "=== Running Database Migrations ==="
alembic upgrade head

echo ""
echo "=== Running Tests ==="
python -m pytest -v --cov=gapi --cov=pulse --cov=shared --cov-report=term-missing

