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

# ✅ FIX: ALWAYS run migrations (Railway TIDAK auto-run)
echo "🔄 Running Prisma migrations..."
if python -m prisma migrate deploy 2>&1; then
    echo "✅ Migrations completed successfully"
else
    echo "⚠️  Migration failed or already applied - continuing anyway"
fi

# Generate Prisma client (ensure latest schema)
echo "🔧 Generating Prisma client..."
python -m prisma generate

# Start application - Railway akan inject $PORT
echo "🚀 Starting Uvicorn on 0.0.0.0:$PORT"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level info