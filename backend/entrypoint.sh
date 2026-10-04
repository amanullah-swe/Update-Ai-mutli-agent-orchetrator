#!/bin/sh
set -e

# Run database migrations before starting the application
echo "[entrypoint] Running database migrations..."
uv run --no-sync alembic -c /app/database/migrations/alembic.ini upgrade head

echo "[entrypoint] Starting application..."
exec "$@"
