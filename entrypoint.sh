#!/bin/bash
set -e

echo "🚀 Starting Keuangan Bot"

if [ -z "$PORT" ]; then
    export PORT=8000
else
    echo "✅ Using Railway PORT: $PORT"
fi

echo "   Environment: ${DEPLOYMENT_ENV:-production}"

# ✅ Use db push instead of migrate deploy
echo "🔄 Pushing Prisma schema to database..."
if python -m prisma db push --skip-generate 2>&1; then
    echo "✅ Schema pushed successfully"
else
    echo "⚠️  Schema push failed - continuing anyway"
fi

echo "🔧 Generating Prisma client..."
python -m prisma generate

echo "🚀 Starting Uvicorn on 0.0.0.0:$PORT"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level info