# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

X-News-Digest is an automated Twitter/X news digest system that collects tweets based on search queries, generates AI-powered summaries using LLMs, and delivers digests via Feishu webhooks or email. The system uses incremental data collection with `since_id` to minimize API calls by 90%+.

**Tech Stack:**
- Backend: FastAPI + Uvicorn (async Python)
- Database: PostgreSQL with Alembic migrations
- Task Queue: Celery + Redis (for scheduled collection and digest generation)
- Frontend: Next.js 16 + React 19 + Tailwind CSS v4
- CLI: Click-based `xndctl` tool
- LLM: Pluggable providers (DeepSeek/OpenAI/GLM) for chat and embeddings
- Data Sources: Twitter API (twitterapi.io), with Mock adapter for testing

## Core Architecture

### Three-Tier System

1. **FastAPI Application** (`app/main.py`)
   - REST API with health checks, CORS, and auto-documented endpoints
   - Routers: users, topics, subscriptions, digests
   - Async database sessions via SQLAlchemy
   - Startup checks for database, Redis, and Celery workers

2. **Celery Workers** (`app/workers/`)
   - `celery_app.py`: Configuration and task auto-discovery
   - `tasks.py`: Core pipeline tasks (collect_data, generate_digest, send_notifications)
   - `beat_schedule.py`: Dynamic cron schedule from database topics
   - All tasks use async/await pattern wrapped in `asyncio.run()`

3. **Web UI** (`webui/`)
   - Next.js App Router with React Server Components
   - SWR for data fetching and caching
   - Responsive design with Tailwind CSS v4
   - Home page redirects to `/archive` for digest browsing

### Data Pipeline Flow

#### Topic-Scoped Pipeline (Legacy)
```
Topic (cron schedule) → Celery Beat → collect_data task
  ↓
TwitterAPIAdapter.fetch_items(since_id=last_tweet_id)
  ↓
Embedding generation + deduplication (by source_id and semantic similarity)
  ↓
Store Items in PostgreSQL (update topic.last_tweet_id)
  ↓
generate_digest task (LLM summarization)
  ↓
send_notifications task → Feishu/Email delivery
```

#### User-Scoped Pipeline (Recommended)
```
User (cron schedule) → Celery Beat → collect_user_topics task
  ↓
For each subscribed topic:
  TwitterAPIAdapter.fetch_items(since_id=topic.last_tweet_id)
  ↓
Aggregate all items from all topics
  ↓
generate_user_digest task (LLM summarization of aggregated items)
  ↓
notify_user_digest task → Feishu/Email delivery
```

**Key Differences:**
- User-scoped pipeline generates a single aggregated digest from all subscribed topics
- Topic-scoped pipeline generates separate digests per topic
- User-scoped is triggered via `POST /users/{user_id}/trigger`
- Topic-scoped is triggered via `POST /topics/{topic_id}/trigger` (deprecated)

### Key Database Models (`app/db/models.py`)

- **User**: Email, Feishu webhook credentials
- **Topic**: Search query, cron schedule, `last_tweet_id` (critical for incremental fetch)
- **Subscription**: Links User ↔ Topic with channel preferences
- **Item**: Raw tweet data with `source_id` (unique), `embedding_hash` (deduplication)
- **Digest**: Generated summary with time window and JSON structure
- **Delivery**: Notification tracking (status, retry_count, error_msg)

### Provider System (`app/services/provider/`)

Factory pattern in `factory.py` returns the correct adapter based on `X_PROVIDER` env var:
- **TwitterAPIAdapter**: Production-ready, uses `since_id` for incremental fetch
- **MockAdapter**: Development/testing with fake data

**Critical**: When adding new providers, implement `fetch_items()` with optional `since_id` parameter to support incremental collection.

### LLM Integration (`app/services/llm/`)

Two separate LLM configurations:
- **Chat API** (`LLM_CHAT_*`): Digest summarization
- **Embedding API** (`LLM_EMBEDDING_*`): Semantic deduplication (supports OpenAI-compatible or Ollama)

Both use retry logic with exponential backoff for rate limit handling.

### CLI Tool (`cli/xndctl/`)

User-friendly CLI wrapping the REST API:
- Interactive prompts with `questionary` for all CRUD operations
- Output formats: table (default), JSON, YAML
- Configuration stored in `~/.xndctl/config.yaml`
- Entry point: `xndctl` command (installed via `pip install -e cli/`)

## Development Commands

### Docker-based Development (Recommended)

```bash
# Start all services (app, worker, beat, postgres, redis)
docker-compose up -d

# View logs
docker-compose logs -f app      # API service
docker-compose logs -f worker   # Task executor
docker-compose logs -f beat     # Scheduler

# Database migrations (see "Database Migrations with Alembic" section below for details)
docker-compose exec app alembic upgrade head

# Run tests
docker-compose exec app pytest tests/ -v

# Run specific test file
docker-compose exec app pytest tests/test_twitter_adapter.py -v

# Test with coverage
docker-compose exec app pytest tests/ --cov=app --cov-report=html

# Code quality (see "Code Quality" section below for details)
docker-compose exec app ruff check app/
docker-compose exec app ruff format --check app/
```

### Local Development (Without Docker)

```bash
# Activate conda environment
./start-local.sh

# Or manually:
conda activate x-news-digest
pip install -r requirements.txt

# Start services individually
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
celery -A app.workers.celery_app beat --loglevel=info

# Monitor Celery tasks with Flower (optional)
celery -A app.workers.celery_app flower --port=5555
# For detailed Flower monitoring, see "Troubleshooting" section below
```

**Note:** Python >=3.10 is required (see `pyproject.toml`). The `start-local.sh` script uses Python 3.13.

### Web UI Development

```bash
cd webui/
npm install
npm run dev      # Development server on http://localhost:3000
npm run build    # Production build
npm run lint     # ESLint
```

### CLI Development

```bash
cd cli/
pip install -e .    # Install in editable mode
xndctl config       # View configuration
xndctl user ls      # Test command
```

## Code Quality

```bash
# Run linter
ruff check app/

# Format code
ruff format app/

# Check formatting without making changes
ruff format --check app/
```

> **Docker equivalent:** See Docker-based Development section above for `docker-compose exec app ruff ...` commands.

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test patterns
pytest tests/ -k "twitter" -v
pytest tests/test_integration_twitter.py::test_incremental_collection -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Note: test_thinking_json_mode.py is excluded in CI but can be run locally
```

> **Docker equivalent:** See Docker-based Development section above for `docker-compose exec app pytest ...` commands.

**Important Test Files:**
- `tests/test_twitter_adapter.py`: Unit tests for Twitter API integration
- `tests/test_integration_twitter.py`: End-to-end incremental collection tests
- `tests/test_thinking_json_mode.py`: LLM JSON mode validation

## Configuration

### Environment Variables (`.env`)

**Critical Variables:**
- `X_PROVIDER`: "TWITTER_API" (production) or "MOCK" (dev/test)
- `TWITTER_API_KEY`: From twitterapi.io (required for TWITTER_API provider)
- `LLM_CHAT_API_KEY` + `LLM_CHAT_BASE_URL`: For digest generation
- `LLM_EMBEDDING_PROVIDER`: "openai" or "ollama"
- `OPENAI_EMBEDDING_API_KEY` + `OPENAI_EMBEDDING_BASE_URL`: If using OpenAI-compatible embeddings
- `EMAIL_LOG_ONLY`: Set to `False` to enable actual email sending (defaults to True)

**Database URLs:**
- Docker: `postgresql+asyncpg://xnews:xnews_password@postgres:5432/xnews_digest`
- Local: Update `.env` with your local PostgreSQL instance

### Timezone Configuration

**CRON_TIMEZONE:** Timezone for cron expressions (default: `Asia/Shanghai` for CST/UTC+8)
- Cron expressions in the database are interpreted in this timezone
- Valid values: IANA timezone names (e.g., `America/New_York`, `Europe/London`, `Asia/Shanghai`)
- Example: If `CRON_TIMEZONE=Asia/Shanghai` and `cron_expression="53 9 * * *"`:
  - Tasks trigger at 9:53 AM CST (China Standard Time)
  - Internally converted to 1:53 AM UTC for Celery Beat
- To use UTC time for cron expressions, set `CRON_TIMEZONE=UTC`

### Multi-Provider LLM Setup

You can use different LLM providers for chat and embeddings. Example configurations:

```bash
# Use DeepSeek for chat, GLM for embeddings
LLM_CHAT_BASE_URL=https://api.deepseek.com
LLM_CHAT_MODEL=deepseek-chat
LLM_CHAT_API_KEY=sk-xxx

LLM_EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_EMBEDDING_MODEL=embedding-3
OPENAI_EMBEDDING_API_KEY=xxx.yyy
```

## Database Migrations with Alembic

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "add new field to topic"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

**Critical Migration:** `002_add_last_tweet_id.py` added the `last_tweet_id` field to Topics table, enabling incremental collection.

## API Documentation

When the app is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health
- Flower (Celery monitoring): http://localhost:5555 (if started)

## CI/CD

The project uses GitHub Actions for CI (`.github/workflows/ci.yml`):
- **Lint job**: Runs Ruff for code quality and formatting checks
- **Test job**: Runs full test suite with PostgreSQL and Redis services
- Python 3.11 is used in CI (local dev supports >=3.10)

## Key Implementation Notes

### Incremental Collection (`since_id`)

The `last_tweet_id` field on Topics enables incremental data collection:

```python
# In tasks.py:collect_data
fetch_kwargs = {
    "query": topic.query,
    "start_date": start_date,
    "end_date": end_date,
    "max_items": 100
}

# Add since_id if available
if topic.last_tweet_id and hasattr(provider, 'fetch_items'):
    sig = inspect.signature(provider.fetch_items)
    if 'since_id' in sig.parameters:
        fetch_kwargs['since_id'] = topic.last_tweet_id
```

After successful collection, update `topic.last_tweet_id` with the highest tweet ID returned.

### Async/Await in Celery Tasks

All Celery tasks follow this pattern:

```python
@celery_app.task(bind=True, name="app.workers.tasks.task_name")
def task_name(self, param: str):
    return asyncio.run(_task_name_async(self, param))

async def _task_name_async(self, param: str):
    async with get_async_session_local()() as session:
        # Async database operations here
        pass
```

### Dynamic Celery Beat Schedule

The `beat_schedule.py` module updates Celery Beat schedule from database on worker startup:

```python
from app.workers.celery_app import celery_app
celery_app.conf.beat_schedule = update_beat_schedule()
```

**Note:** Changes to Topic cron schedules require a Beat restart to take effect.

**Celery Beat Schedule Files:** The `celerybeat-schedule*` database files are generated at runtime by Celery Beat and excluded from version control via `.gitignore`. These files store the scheduler's internal state and should not be committed to the repository.

### Embedding-Based Deduplication

Items are deduplicated using both:
1. **Source ID uniqueness**: PostgreSQL unique constraint on `items.source_id`
2. **Semantic similarity**: `embedding_hash` comparison with cosine similarity threshold

See `app/db/utils.py:check_duplicate_by_embedding()` for implementation.

## Common Development Workflows

### Adding a New API Endpoint

1. Define Pydantic schemas in `app/api/schemas.py` or resource-specific file
2. Add route function in appropriate router (`app/api/topics.py`, etc.)
3. Update `app/main.py` if adding a new router
4. Test via Swagger UI or write integration test

### Adding a New Celery Task

1. Define async implementation in `app/workers/tasks.py`
2. Wrap in sync task decorator: `@celery_app.task(bind=True)`
3. Add to `celery_app.conf.include` if in separate module
4. Test with `celery.send_task()` or direct invocation

### Creating a New Data Provider

1. Implement `BaseProvider` interface in `app/services/provider/`
2. Add to factory in `factory.py` with new env var check
3. Support `since_id` parameter for incremental collection
4. Add unit tests in `tests/test_<provider>_adapter.py`

### Database Schema Changes

1. Modify models in `app/db/models.py`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review and edit generated migration in `alembic/versions/`
4. Apply: `alembic upgrade head`
5. Update schemas in `app/api/schemas.py` if needed

## Troubleshooting

### Local Development Logs

When using `start-local.sh`, service logs are written to:
- FastAPI: `/tmp/fastapi.log`
- Celery Worker: `/tmp/celery_worker.log`
- Celery Beat: `/tmp/celery_beat.log`

View them with: `tail -f /tmp/fastapi.log`

### Celery Tasks Not Running

```bash
# Check Beat is scheduling tasks
docker-compose logs beat | grep "Scheduler"

# Verify worker is receiving tasks
docker-compose logs worker | grep "received"

# Inspect Celery stats
docker-compose exec worker celery -A app.workers.celery_app inspect active
docker-compose exec worker celery -A app.workers.celery_app inspect registered

# Check Flower UI for real-time task monitoring
# Start: celery -A app.workers.celery_app flower --port=5555
# Visit: http://localhost:5555
```

### Database Connection Issues

```bash
# Check PostgreSQL is healthy
docker-compose exec postgres pg_isready -U xnews

# Connect to database
docker-compose exec postgres psql -U xnews -d xnews_digest

# View tables
\dt

# Check topic last_tweet_id values
SELECT name, last_tweet_id FROM topics;
```

### Twitter API Rate Limits

The TwitterAPIAdapter respects twitterapi.io rate limits (20 tweets per page, max 5 pages = 100 tweets). Adjust `TWITTER_API_MAX_PAGES` in `.env` if needed.

### LLM Embedding Rate Limits

Configured with automatic retry logic:
- `LLM_EMBEDDING_RETRY_MAX_ATTEMPTS`: Default 5
- `LLM_EMBEDDING_RETRY_INITIAL_BACKOFF`: Default 1.0 seconds
- Exponential backoff on HTTP 429 responses

## Project Structure Reference

```
x-news-digest/
├── app/
│   ├── api/              # FastAPI routers and Pydantic schemas
│   ├── core/             # config.py (Settings), logging.py
│   ├── db/               # SQLAlchemy models, session, utilities
│   ├── services/
│   │   ├── provider/     # Data source adapters (Twitter, Mock)
│   │   ├── llm/          # LLM client for chat and embeddings
│   │   ├── embedding/    # OpenAI and Ollama embedding providers
│   │   └── notifier/     # Feishu and email delivery
│   ├── workers/          # Celery app, tasks, beat schedule
│   └── main.py           # FastAPI application entry point
├── alembic/              # Database migrations
├── cli/xndctl/           # CLI tool (Click-based)
├── webui/                # Next.js frontend
│   ├── app/              # Next.js App Router pages
│   ├── components/       # React components
│   └── lib/              # API client, utilities
├── tests/                # Pytest test suite
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Application container
├── requirements.txt      # Python dependencies
└── .env.example          # Environment variable template
```

## CLI Usage Summary

```bash
# User management
xndctl user create -p              # Interactive create
xndctl user ls                     # List all users
xndctl user get --name "John"      # Get user details
xndctl user update --name "John" -p
xndctl user delete --name "John"

# Topic management
xndctl topic create -p             # Interactive with cron validation
xndctl topic ls
xndctl topic update --name "AI News" --enable

# Subscriptions
xndctl sub create -p               # Must use interactive mode
xndctl sub ls --user-id <uuid>

# Manual triggers
xndctl trigger -p                  # Select topic to collect
xndctl notify -p                   # Select digest to send

# Configuration
xndctl config                      # View current config
xndctl init                        # Reinitialize config
```
