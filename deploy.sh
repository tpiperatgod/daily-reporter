#!/bin/bash
# X-News-Digest Production Deployment Script
set -e

DO_PULL=true
BUILD_ONLY=false

for arg in "$@"; do
    case $arg in
        --no-pull)   DO_PULL=false ;;
        --build-only) BUILD_ONLY=true ;;
        *)
            echo "Usage: ./deploy.sh [--no-pull] [--build-only]"
            echo "  --no-pull      Skip git pull, deploy current code"
            echo "  --build-only   Build images without restarting"
            exit 1
            ;;
    esac
done

echo "=== X-News-Digest Production Deploy ==="
echo ""

# ── Step 1: Validate prerequisites ──
echo "[1/5] Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose v2 is required (docker compose, not docker-compose)"
    exit 1
fi

if [ ! -f .env ]; then
    echo "ERROR: .env file not found"
    exit 1
fi

echo "  Prerequisites OK"

# ── Step 2: Git pull ──
if [ "$DO_PULL" = true ]; then
    echo ""
    echo "[2/5] Pulling latest code..."

    if [ -n "$(git status --porcelain)" ]; then
        echo "ERROR: Working directory has uncommitted changes. Commit or stash first."
        exit 1
    fi

    git pull origin main
    echo "  Pull complete"
else
    echo ""
    echo "[2/5] Skipping git pull (--no-pull)"
fi

# ── Step 3: Build images ──
echo ""
echo "[3/5] Building production images..."
docker compose --profile prod build
echo "  Build complete"

if [ "$BUILD_ONLY" = true ]; then
    echo ""
    echo "Build finished (--build-only). Skipping restart."
    exit 0
fi

# ── Step 4: Restart containers ──
echo ""
echo "[4/5] Restarting services..."

# Ensure infrastructure is running
docker compose up -d postgres redis

# Stop app services only (infra keeps running)
docker compose --profile prod stop app-prod worker-prod beat-prod 2>/dev/null || true

# Start all prod services
docker compose --profile prod up -d
echo "  Services restarted"

# ── Step 5: Health check ──
echo ""
echo "[5/5] Waiting for health check..."

MAX_WAIT=60
INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "  Health check passed!"
        echo ""
        echo "=== Deployment successful ==="
        echo ""
        docker compose --profile prod ps
        echo ""
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
        exit 0
    fi
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
    echo "  Waiting... (${ELAPSED}s / ${MAX_WAIT}s)"
done

echo ""
echo "WARNING: Health check did not pass within ${MAX_WAIT}s"
echo "Check logs: docker compose --profile prod logs -f app-prod"
docker compose --profile prod ps
exit 1
