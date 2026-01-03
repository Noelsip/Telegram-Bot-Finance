#!/bin/sh
set -e

echo "🚀 Starting Keuangan Bot"
echo "   PORT: ${PORT:-8000}"
echo "   Environment: ${DEPLOYMENT_ENV:-production}"

# Run Prisma migrations (Railway auto-handles, but safe to run)
if [ "$DEPLOYMENT_ENV" = "railway" ]; then
    echo "⏭️  Skipping manual migrations (Railway auto-runs)"
else
    echo "🔄 Running Prisma migrations..."
    python -m prisma migrate deploy || echo "⚠️  Migration warning (may already be applied)"
fi

# Start application
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info