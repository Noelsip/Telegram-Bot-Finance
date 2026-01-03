#!/bin/bash
set -e

echo "🚀 Starting Keuangan Bot"

# Railway akan inject PORT environment variable
if [ -z "$PORT" ]; then
    export PORT=8000
    echo "⚠️  PORT not set, using default: 8000"
else
    echo "✅ Using Railway PORT: $PORT"
fi

echo "   Environment: ${DEPLOYMENT_ENV:-production}"
echo "   Database: ${DATABASE_URL:0:30}..."

# Skip migrations di Railway (auto-handled)
if [ "$DEPLOYMENT_ENV" = "railway" ]; then
    echo "⏭️  Skipping manual migrations (Railway auto-runs)"
else
    echo "🔄 Running Prisma migrations..."
    python -m prisma migrate deploy 2>&1 || echo "⚠️  Migration warning (may already be applied)"
fi

# Start application - Railway akan inject $PORT
echo "🚀 Starting Uvicorn on 0.0.0.0:$PORT"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level info