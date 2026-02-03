#!/bin/bash
# X-News-Digest 启动脚本

set -e

echo "🚀 X-News-Digest 启动脚本"
echo "=========================="
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未安装 Docker"
    echo "请访问 https://docs.docker.com/get-docker/ 安装 Docker"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: 未安装 Docker Compose"
    echo "请访问 https://docs.docker.com/compose/install/ 安装 Docker Compose"
    exit 1
fi

echo "✅ Docker 环境检查通过"
echo ""

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，从 .env.example 复制..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件"
    echo ""
    echo "⚠️  重要: 请编辑 .env 文件，配置以下必需参数："
    echo "   - TWITTER_API_KEY (从 https://twitterapi.io 获取)"
    echo "   - LLM_API_KEY (从 https://platform.deepseek.com 获取)"
    echo ""
    read -p "是否现在编辑 .env 文件? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-vi} .env
    else
        echo "请稍后手动编辑 .env 文件后再启动服务"
        exit 0
    fi
fi

# 检查必需的环境变量
echo "🔍 检查环境变量配置..."
source .env

if [ "$X_PROVIDER" = "TWITTER_API" ] && [ -z "$TWITTER_API_KEY" ]; then
    echo "❌ 错误: TWITTER_API_KEY 未配置"
    echo "请在 .env 文件中设置 TWITTER_API_KEY"
    exit 1
fi

if [ -z "$LLM_CHAT_API_KEY" ]; then
    echo "❌ 错误: LLM_CHAT_API_KEY 未配置"
    echo "请在 .env 文件中设置 LLM_CHAT_API_KEY"
    exit 1
fi

echo "✅ 环境变量配置检查通过"
echo ""

# 询问是否启动服务
echo "准备启动以下服务:"
echo "  - PostgreSQL (数据库)"
echo "  - Redis (消息队列)"
echo "  - API Server (FastAPI)"
echo "  - Worker (Celery 任务执行器)"
echo "  - Beat (Celery 定时调度器)"
echo ""
read -p "是否继续启动? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消启动"
    exit 0
fi

# 启动服务
echo ""
echo "🚀 启动服务..."
echo ""

docker-compose up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker-compose ps

echo ""
echo "🔍 健康检查..."
sleep 5

# 检查 API 健康状态
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ API 服务健康"
else
    echo "⚠️  API 服务可能还在启动中，请稍后访问 http://localhost:8000/health 检查"
fi

echo ""
echo "=========================="
echo "🎉 启动完成！"
echo ""
echo "📚 访问以下地址:"
echo "  - API 文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/health"
echo ""
echo "📝 查看日志:"
echo "  docker-compose logs -f"
echo ""
echo "🛑 停止服务:"
echo "  docker-compose down"
echo ""
echo "📖 更多帮助请查看: QUICKSTART.md"
echo "=========================="
