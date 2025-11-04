#!/usr/bin/env bash
set -euo pipefail

# Run migrations
alembic upgrade head

# Start API
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
