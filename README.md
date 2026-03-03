# X-News-Digest

基于 Twitter API 的自动化新闻摘要系统，使用 LLM 生成智能摘要并通过飞书/邮件推送。

## 核心功能

- 🐦 **Twitter 数据收集**：支持 Twitter API、Mock 两种数据源
- 🔄 **增量采集**：使用 `since_id` 机制，仅获取新推文（节省 90%+ API 调用）
- 🤖 **AI 摘要**：集成 DeepSeek/OpenAI/GLM 生成智能摘要
- 📅 **定时任务**：基于 Cron 表达式的自动化采集
- 📧 **多渠道推送**：支持飞书 Webhook 和邮件通知
- 🎯 **去重机制**：基于 embedding 的语义去重
- 📊 **RESTful API**：完整的 API + Swagger 文档

## 技术栈

- **后端**：FastAPI + Uvicorn
- **数据库**：PostgreSQL + Alembic (异步 ORM)
- **任务队列**：Celery + Redis
- **数据源**：Twitter API (twitterapi.io)
- **LLM**：DeepSeek / OpenAI / GLM
- **容器化**：Docker + Docker Compose
- **前端**：Next.js 16 + React 19 + Tailwind CSS v4
- **CLI**：Click-based `xndctl` 工具

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd x-news-digest
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置必需参数
```

**最小配置**：

```bash
X_PROVIDER=TWITTER_API
TWITTER_API_KEY=your_twitter_api_key_here

LLM_CHAT_API_KEY=your_chat_api_key_here
LLM_EMBEDDING_API_KEY=your_embedding_api_key_here
```

### 3. 启动服务

```bash
# 开发模式（推荐）
docker-compose --profile dev up -d

# 生产模式
docker-compose --profile prod up -d

# 查看日志
docker-compose logs -f
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# API 文档
open http://localhost:8000/docs
```

### 5. 创建第一个摘要

```bash
# 安装 CLI
cd cli && pip install -e .

# 创建用户
xndctl user create -p

# 创建 Topic
xndctl topic create -p

# 触发用户级采集
xndctl trigger -p

## 核心特性

### 1. 用户级聚合触发

系统支持**用户级聚合触发**，一次触发收集用户所有 Topic 的数据并生成单一聚合摘要：

```bash
# 触发用户所有 Topic 的采集
POST /api/v1/users/{user_id}/trigger
```

**流程**：
1. 收集用户 `topics` 列表中的所有 Topic 数据
2. 生成单一聚合摘要
3. 根据用户级通知渠道设置（`enable_feishu`, `enable_email`）推送通知

### 2. 增量采集（since_id）

使用 `since_id` 参数只获取新推文，大幅减少 API 调用：

```
第一次: 获取 1000 条推文，记录 last_tweet_id = 12345
第二次: 获取 since_id:12345 之后的 10 条新推文
第三次: 获取 since_id:12356 之后的 5 条新推文
```

**成本节省**：90%+ 的 API 调用减少

### 3. 智能去重

- **Source ID 去重**：推文 ID 唯一性检查
- **Embedding 去重**：语义相似度检测（转发/引用）

## API 概览

### 核心端点

| 资源 | 端点 | 说明 |
|------|------|------|
| Users | `POST /api/v1/users` | 创建用户 |
| | `POST /api/v1/users/{id}/trigger` | **触发用户摘要** |
| Topics | `POST /api/v1/topics` | 创建 Topic |
| | `GET /api/v1/topics` | 列出 Topics |
| Digests | `GET /api/v1/digests` | 列出摘要 |
| | `POST /api/v1/digests/{id}/send` | 手动发送（需 `user_id`） |
**完整 API 文档**：运行后访问 `http://localhost:8000/docs`

## 常用命令

```bash
# Docker 操作
docker-compose --profile dev up -d    # 启动开发环境
docker-compose down                   # 停止服务
docker-compose logs -f app            # 查看日志

# 数据库迁移
docker-compose exec app alembic upgrade head

# CLI 操作
xndctl user ls                        # 列出用户
xndctl topic ls                       # 列出 Topics
xndctl trigger -p                     # 触发采集
xndctl notify -p                      # 发送通知

# 测试
docker-compose exec app pytest tests/ -v
```

## 项目结构

```
x-news-digest/
├── app/
│   ├── api/              # API 路由
│   ├── core/             # 配置和日志
│   ├── db/               # 数据库模型
│   ├── services/         # 业务逻辑
│   │   ├── provider/     # 数据源适配器
│   │   ├── llm/          # LLM 客户端
│   │   └── notifier/     # 通知服务
│   └── workers/          # Celery 任务
├── cli/xndctl/           # CLI 工具
├── webui/                # Next.js 前端
├── tests/                # 测试
├── alembic/              # 数据库迁移
└── docker-compose.yml    # Docker 编排
```

## 配置说明

### 环境变量

**必需配置**：

```bash
# 数据源
X_PROVIDER=TWITTER_API              # 或 MOCK
TWITTER_API_KEY=your_key_here

# LLM (Chat)
LLM_CHAT_BASE_URL=https://api.openai.com/v1
LLM_CHAT_MODEL=gpt-4-turbo
LLM_CHAT_API_KEY=your_key_here

# LLM (Embedding)
LLM_EMBEDDING_PROVIDER=openai       # 或 ollama
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_API_KEY=your_key_here
```

**可选配置**：

```bash
# 时区（默认：Asia/Shanghai）
CRON_TIMEZONE=Asia/Shanghai

# 邮件（默认：log_only=true）
EMAIL_LOG_ONLY=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

## 监控

### 健康检查

```bash
GET /health
```

返回组件状态：
- Database：数据库连接
- Redis：缓存连接
- Celery：任务队列

### Celery 监控

```bash
# 启动 Flower（可选）
celery -A app.workers.celery_app flower --port=5555

# 访问
open http://localhost:5555
```

## 故障排查

### 服务无法启动

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs app
docker-compose logs worker
```

### API 调用失败

```bash
# 检查健康状态
curl http://localhost:8000/health

# 检查 Celery
docker-compose exec worker celery -A app.workers.celery_app inspect active
```

### CLI 连接失败

```bash
# 检查配置
xndctl config

# 重新初始化
xndctl init
```

## 文档

- **[CLI 文档](cli/README.md)** - xndctl 命令行工具使用指南
- **[API 文档](http://localhost:8000/docs)** - 运行后访问 Swagger UI
- **[环境变量](.env.example)** - 完整配置示例

## 许可证

MIT License

## 致谢

- [twitterapi.io](https://twitterapi.io) - Twitter API 服务
- [FastAPI](https://fastapi.tiangolo.com) - Web 框架
- [Celery](https://docs.celeryproject.org) - 任务队列

## Breaking Changes

### v2.0 - Subscription System Removal

**Migration Date**: 2026-03-03

The subscription system has been completely removed and replaced with a simpler user-topics relationship:

#### API Changes

- **Removed**: All `/api/v1/subscriptions` endpoints
- **Changed**: `POST /api/v1/users` now accepts `topics` (UUID array), `enable_feishu`, `enable_email`
- **Changed**: `POST /api/v1/digests/{id}/send` now requires `user_id` instead of `subscription_id`
- **Deprecated**: Topic-scoped notification pipeline (`notify` task is now a stub)

#### CLI Changes

- **Removed**: `xndctl sub` command group entirely
- **Changed**: Workflow now uses `user.topics` to associate topics with users
- **Changed**: Notification channels configured at user level, not per subscription

#### Data Model Changes

- **Removed**: `subscriptions` table (dropped from database)
- **Added**: `users.topics` JSONB array for topic associations
- **Added**: `users.enable_feishu` and `users.enable_email` boolean flags
- **Migration**: Existing subscription data migrated to `users.topics` with OR-aggregated channel flags

#### Migration Path

1. **Before**: User → Subscription → Topic (many-to-many with channel preferences)
2. **After**: User → `topics` array + user-level channel flags
3. **Impact**: Simpler mental model - ALL topics receive notifications via ALL enabled channels

For detailed migration implementation, see `alembic/versions/20260303_0914_a5e1d178682a_users_topics_redesign.py`
