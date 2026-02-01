# X-News-Digest

基于 Twitter API 的自动化新闻摘要系统，使用 LLM 生成智能摘要并通过飞书/邮件推送。

## ✨ 核心功能

- 🐦 **Twitter 数据收集**：支持 Twitter API、Apify、Mock 三种数据源
- 🔄 **增量采集**：使用 `since_id` 机制，仅获取新推文（节省 90%+ API 调用）
- 🤖 **AI 摘要**：集成 DeepSeek/OpenAI LLM 生成智能摘要
- 📅 **定时任务**：基于 Cron 表达式的自动化采集
- 📧 **多渠道推送**：支持飞书 Webhook 和邮件通知
- 🎯 **去重机制**：基于 embedding 的语义去重
- 📊 **完整 API**：RESTful API + Swagger 文档

## 🏗️ 技术栈

- **后端框架**：FastAPI + Uvicorn
- **数据库**：PostgreSQL + Alembic (异步 ORM)
- **任务队列**：Celery + Redis
- **数据源**：Twitter API (twitterapi.io)
- **LLM**：DeepSeek / OpenAI / GLM（支持 Chat 和 Embedding 使用不同 provider）
- **容器化**：Docker + Docker Compose

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd x-news-digest
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置以下必需参数：
# - TWITTER_API_KEY (从 https://twitterapi.io 获取)
# - LLM_CHAT_API_KEY 和 LLM_EMBEDDING_API_KEY
# - SMTP 配置（如需邮件通知）
```

**最小配置示例：**

```bash
# Provider
X_PROVIDER=TWITTER_API
TWITTER_API_KEY=your_twitter_api_key_here

# LLM - 可使用相同或不同的 provider
LLM_CHAT_API_KEY=your_chat_api_key_here
LLM_EMBEDDING_API_KEY=your_embedding_api_key_here

# 其他使用默认值即可
```

### 3. 启动服务

```bash
# 启动所有服务（首次启动会自动构建镜像和运行数据库迁移）
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 4. 验证服务

```bash
# 检查健康状态
curl http://localhost:8000/health

# 访问 API 文档
open http://localhost:8000/docs
```

### 5. 创建第一个 Topic

```bash
# 创建用户
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com"}'

# 创建 Topic（监控 @karpathy 的推文）
curl -X POST http://localhost:8000/api/v1/topics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Karpathy Updates",
    "query": "@karpathy",
    "cron_expression": "0 9 * * *"
  }'

# 手动触发采集（替换 {topic_id}）
curl -X POST http://localhost:8000/api/v1/topics/{topic_id}/trigger
```

## 📚 文档

- **[快速开始指南](QUICKSTART.md)** - 详细的部署和配置说明
- **[Twitter API 集成指南](docs/twitter-api-integration.md)** - API 文档和使用示例
- **[实现总结](IMPLEMENTATION_SUMMARY.md)** - 技术实现细节

## 🏛️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                         用户                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (REST API)                        │
│  - 用户管理  - Topic 管理  - 手动触发  - 查询数据          │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│   Celery Beat (调度)      │   │   Celery Worker (执行)   │
│  - 定时触发采集任务       │   │  - 数据采集              │
│  - 更新任务调度           │   │  - 摘要生成              │
└──────────────────────────┘   │  - 通知推送              │
                               └──────────────────────────┘
                                         │
                ┌────────────────────────┼────────────────────┐
                ▼                        ▼                    ▼
┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Twitter API         │  │  LLM APIs        │  │  PostgreSQL      │
│  - 推文采集          │  │  - Chat (摘要)   │  │  - 数据存储      │
│  - 增量更新          │  │  - Embedding去重 │  │  - 状态管理      │
└──────────────────────┘  └──────────────────┘  └──────────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────┐
                          │   通知渠道                │
                          │  - 飞书 Webhook          │
                          │  - 邮件推送              │
                          └──────────────────────────┘
```

## 🔑 核心特性

### 1. 增量采集（since_id）

传统方式每次获取所有历史推文，浪费 API 额度：
```
第一次: 获取 1000 条推文
第二次: 获取 1000 条推文 (990 条重复)
第三次: 获取 1000 条推文 (995 条重复)
```

使用 `since_id` 只获取新推文：
```
第一次: 获取 1000 条推文，记录 last_tweet_id = 12345
第二次: 获取 since_id:12345 之后的 10 条新推文
第三次: 获取 since_id:12356 之后的 5 条新推文
```

**成本节省：90%+ 的 API 调用减少**

### 2. 智能去重

- **Source ID 去重**：推文 ID 唯一性检查
- **Embedding 去重**：语义相似度检测（转发/引用）

### 3. 多 Provider 支持

| Provider | 成本 | 速度 | 推荐场景 |
|----------|------|------|----------|
| Twitter API | 低 | 快 | 生产环境 ✅ |
| Apify | 高 | 中 | 需要更多数据 |
| Mock | 免费 | 即时 | 开发测试 |

切换 Provider 只需修改 `.env` 中的 `X_PROVIDER`。

## 📊 数据流程

```
1. 定时触发 (Celery Beat)
   └─> 2. 数据采集 (Worker Task)
       ├─> 3. 调用 Twitter API (TwitterAPIAdapter)
       │   └─> 使用 since_id 获取新推文
       ├─> 4. 生成 Embedding (LLM)
       ├─> 5. 去重检查 (Database)
       └─> 6. 存储数据 (PostgreSQL)
           └─> 7. 生成摘要 (LLM)
               └─> 8. 推送通知 (飞书/邮件)
```

## 🧪 测试

```bash
# 运行所有测试
docker-compose exec app pytest tests/ -v

# 运行单元测试
docker-compose exec app pytest tests/test_twitter_adapter.py -v

# 运行集成测试
docker-compose exec app pytest tests/test_integration_twitter.py -v

# 测试覆盖率
docker-compose exec app pytest tests/ --cov=app --cov-report=html
```

## 🔧 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f app      # API 服务
docker-compose logs -f worker   # 任务执行器
docker-compose logs -f beat     # 定时调度器

# 重启服务
docker-compose restart worker

# 进入数据库
docker-compose exec postgres psql -U xnews -d xnews_digest

# 运行数据库迁移
docker-compose exec app alembic upgrade head

# 查看 Celery 任务
docker-compose exec worker celery -A app.workers.celery_app inspect active
```

## 📁 项目结构

```
x-news-digest/
├── app/
│   ├── api/              # API 路由和 schemas
│   ├── core/             # 核心配置和日志
│   ├── db/               # 数据库模型和会话
│   ├── services/
│   │   ├── provider/     # 数据源适配器
│   │   │   ├── twitter_adapter.py  # Twitter API 集成 ⭐
│   │   │   ├── apify_adapter.py
│   │   │   └── mock_adapter.py
│   │   ├── llm/          # LLM 客户端
│   │   └── notifier/     # 通知服务
│   └── workers/          # Celery 任务
├── alembic/              # 数据库迁移
│   └── versions/
│       ├── 001_initial_schema.py
│       └── 002_add_last_tweet_id.py  # 新增 ⭐
├── tests/                # 测试
│   ├── test_twitter_adapter.py       # 单元测试 ⭐
│   └── test_integration_twitter.py   # 集成测试 ⭐
├── docs/
│   └── twitter-api-integration.md    # API 文档 ⭐
├── docker-compose.yml    # Docker 编排
├── Dockerfile           # 应用镜像
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
├── QUICKSTART.md        # 快速开始指南 ⭐
└── README.md           # 项目说明
```

## 🌟 最新更新 (2025-01-31)

### ✅ Twitter API 直接集成

- ✨ 新增 `TwitterAPIAdapter` - 直接调用 twitterapi.io API
- 🚀 增量采集 - 使用 `since_id` 参数，减少 90%+ API 调用
- 📊 数据库升级 - 新增 `last_tweet_id` 字段追踪采集进度
- 🧪 完整测试 - 单元测试 + 集成测试覆盖 >90%
- 📖 详细文档 - 完整的 API 集成指南和使用示例

### 🎯 升级指南

从 Apify 迁移到 Twitter API：

```bash
# 1. 更新代码
git pull

# 2. 运行数据库迁移
docker-compose exec app alembic upgrade head

# 3. 修改 .env
X_PROVIDER=TWITTER_API
TWITTER_API_KEY=your_twitter_api_key_here

# 4. 重启服务
docker-compose restart worker
```

回滚到 Apify：

```bash
# 修改 .env
X_PROVIDER=APIFY

# 重启服务
docker-compose restart worker
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [twitterapi.io](https://twitterapi.io) - Twitter API 服务
- [DeepSeek](https://platform.deepseek.com) - LLM 服务
- [FastAPI](https://fastapi.tiangolo.com) - Web 框架
- [Celery](https://docs.celeryproject.org) - 分布式任务队列

---

**Happy Digesting! 📰✨**
