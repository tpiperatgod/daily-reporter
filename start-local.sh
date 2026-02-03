#!/bin/bash

# X-News-Digest 本地开发启动脚本
# 使用: ./start-local.sh

set -e  # 遇到错误立即退出

echo "🚀 Starting X-News-Digest in local development mode..."
echo ""

# 检查并激活 conda 环境
CONDA_BASE="/Users/laminar/anaconda3"
CONDA_ENV="x-news-digest"

if ! "$CONDA_BASE/bin/conda" env list | grep -q "^$CONDA_ENV "; then
    echo "❌ Conda environment '$CONDA_ENV' not found!"
    echo "   Please run: conda create -n $CONDA_ENV python=3.13"
    echo "   Then: conda activate $CONDA_ENV && pip install -r requirements.txt"
    exit 1
fi

# 激活 conda 环境
eval "$("$CONDA_BASE/bin/conda" shell.bash hook)"
conda activate "$CONDA_ENV"

if [ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]; then
    echo "❌ Failed to activate conda environment '$CONDA_ENV'"
    exit 1
fi

echo "✅ Using conda environment: $CONDA_DEFAULT_ENV"

# 启动依赖服务
echo "📦 Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

# 等待服务健康检查通过
echo "⏳ Waiting for services to be healthy..."
sleep 5

# 验证 PostgreSQL
echo "🔍 Checking PostgreSQL..."
if docker-compose exec -T postgres pg_isready -U xnews > /dev/null 2>&1; then
    echo "   ✅ PostgreSQL is ready"
else
    echo "   ❌ PostgreSQL is not ready"
    exit 1
fi

# 验证 Redis
echo "🔍 Checking Redis..."
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis is ready"
else
    echo "   ❌ Redis is not ready"
    exit 1
fi

echo ""
echo "📝 Starting application services..."
echo "   Use Ctrl+C to stop all services"
echo ""

# 清理函数
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "celery.*app.workers.celery_app worker" 2>/dev/null || true
    pkill -f "celery.*app.workers.celery_app beat" 2>/dev/null || true
    echo "   ✅ All services stopped"
    exit 0
}

# 注册清理函数
trap cleanup INT TERM

# 启动 FastAPI
echo "🌐 Starting FastAPI on http://localhost:8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/fastapi.log 2>&1 &
FASTAPI_PID=$!

# 等待 FastAPI 启动
sleep 4

# 检查 FastAPI 是否成功启动
if ps -p $FASTAPI_PID > /dev/null 2>&1; then
    echo "   ✅ FastAPI started (PID: $FASTAPI_PID)"
else
    echo "   ❌ FastAPI failed to start. Check /tmp/fastapi.log"
    exit 1
fi

# 启动 Celery Worker
echo "⚙️  Starting Celery Worker..."
celery -A app.workers.celery_app worker --pool=solo --loglevel=info > /tmp/celery_worker.log 2>&1 &
WORKER_PID=$!

# 等待 Celery Worker 启动
sleep 4

# 检查 Celery Worker 是否成功启动
if ps -p $WORKER_PID > /dev/null 2>&1; then
    echo "   ✅ Celery Worker started (PID: $WORKER_PID)"
else
    echo "   ❌ Celery Worker failed to start. Check /tmp/celery_worker.log"
    kill $FASTAPI_PID 2>/dev/null || true
    exit 1
fi

# 启动 Celery Beat（可选）
echo "⏰ Starting Celery Beat..."
celery -A app.workers.celery_app beat --loglevel=info > /tmp/celery_beat.log 2>&1 &
BEAT_PID=$!

# 等待 Celery Beat 启动
sleep 2

if ps -p $BEAT_PID > /dev/null 2>&1; then
    echo "   ✅ Celery Beat started (PID: $BEAT_PID)"
else
    echo "   ⚠️  Celery Beat failed to start (optional service)"
fi

echo ""
echo "✅ Health check..."
if command -v jq > /dev/null 2>&1; then
    curl -s http://localhost:8000/health | jq .
else
    curl -s http://localhost:8000/health
fi

echo ""
echo "🎉 All services started successfully!"
echo ""
echo "📚 API Documentation: http://localhost:8000/docs"
echo "🏥 Health Check:      http://localhost:8000/health"
echo ""
echo "📋 Logs:"
echo "   FastAPI:       tail -f /tmp/fastapi.log"
echo "   Celery Worker: tail -f /tmp/celery_worker.log"
echo "   Celery Beat:   tail -f /tmp/celery_beat.log"
echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# 保持脚本运行
wait
