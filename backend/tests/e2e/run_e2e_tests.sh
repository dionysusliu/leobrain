#!/bin/bash
# Script to run E2E tests with proper setup

set -e

echo "🚀 Starting E2E Test Setup..."

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if services are running
echo "📋 Checking Docker services..."
SERVICES=$(docker ps --filter "name=leobrain-" --format "{{.Names}}")

if [ -z "$SERVICES" ]; then
    echo "⚠️  Docker services not running. Starting them..."
    cd "$(dirname "$0")/../../.."
    docker compose up -d
    
    echo "⏳ Waiting for services to be ready..."
    sleep 10
else
    echo "✅ Docker services are running:"
    echo "$SERVICES"
fi

# Check PostgreSQL
echo "🔍 Checking PostgreSQL..."
for i in {1..30}; do
    if docker exec leobrain-postgres pg_isready -U leobrain > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL not ready after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Check MinIO
echo "🔍 Checking MinIO..."
for i in {1..30}; do
    if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        echo "✅ MinIO is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ MinIO not ready after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Run tests
echo "🧪 Running E2E tests..."
# cd "$(dirname "$0")/.."
pytest tests/e2e/ -v -m e2e "$@"

echo "✅ E2E tests completed!"

