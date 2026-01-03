#!/bin/bash
set -e

echo "🚀 Starting Keuangan Bot"
echo "========================================="

# Set default PORT if not provided
if [ -z "$PORT" ]; then
    export PORT=8000
    echo "⚠️  PORT not set, using default: $PORT"
else
    echo "✅ Using Railway PORT: $PORT"
fi

echo "   Environment: ${DEPLOYMENT_ENV:-production}"
echo "   Database: ${DATABASE_URL:0:50}..."
echo "========================================="

# ✅ Sync schema ke database (tanpa migration files)
echo ""
echo "🔄 Syncing Prisma schema to database..."
if python -m prisma db push --accept-data-loss 2>&1; then
    echo "✅ Schema synced successfully"
else
    echo "⚠️  Schema sync failed - will retry on next restart"
    # Don't exit - let app try to start anyway
fi

# ✅ Generate Prisma client
echo ""
echo "🔧 Generating Prisma client..."
python -m prisma generate

# ✅ Start application
echo ""
echo "🚀 Starting Uvicorn on 0.0.0.0:$PORT"
echo "========================================="
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level info