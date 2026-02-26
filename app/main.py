from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import time
import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.workers.celery_app import celery_app
from app.api.schemas import HealthResponse, ComponentHealth

# Setup logging
logger = setup_logging("app")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="X-News-Digest: Automated Twitter/X topic monitoring and digest service",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def check_database():
    """Check database connectivity."""
    start_time = time.time()
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to test connection
            await session.execute(text("SELECT 1"))
            latency = (time.time() - start_time) * 1000
            return ComponentHealth(
                status="healthy",
                message="Database connection successful",
                latency_ms=round(latency, 2),
            )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ComponentHealth(status="unhealthy", message=str(e))


async def check_redis():
    """Check Redis connectivity."""
    start_time = time.time()
    try:
        client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await client.ping()
        await client.close()
        latency = (time.time() - start_time) * 1000
        return ComponentHealth(
            status="healthy",
            message="Redis connection successful",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return ComponentHealth(status="unhealthy", message=str(e))


async def check_celery():
    """Check Celery worker availability."""
    start_time = time.time()
    try:
        # Check if we can inspect Celery
        inspector = celery_app.control.inspect()
        stats = inspector.stats()

        if stats:
            # Workers are running
            worker_count = len(stats)
            latency = (time.time() - start_time) * 1000
            return ComponentHealth(
                status="healthy",
                message=f"{worker_count} worker(s) available",
                latency_ms=round(latency, 2),
            )
        else:
            # No workers running but broker is reachable
            return ComponentHealth(status="degraded", message="No workers running (broker reachable)")
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return ComponentHealth(status="unhealthy", message=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint with real service status.

    Returns:
        HealthResponse: Status of all system components
    """
    # Check all components
    db_health = await check_database()
    redis_health = await check_redis()
    celery_health = await check_celery()

    # Determine overall status
    components = {"database": db_health, "redis": redis_health, "celery": celery_health}

    # Overall status is healthy if all critical components are healthy
    all_healthy = all(c.status == "healthy" for c in components.values())
    any_degraded = any(c.status == "degraded" for c in components.values())

    if any_degraded and not all_healthy:
        overall_status = "degraded"
    elif all_healthy:
        overall_status = "healthy"
    else:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        components=components,
    )


@app.get("/")
async def root():
    """
    Root endpoint.

    Returns:
        dict: Basic app information
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs_url": "/docs",
        "health_url": "/health",
    }


# Register API routers
from app.api import users, topics, subscriptions, digests

app.include_router(users.router, prefix="/api/v1", tags=["users"])

app.include_router(topics.router, prefix="/api/v1", tags=["topics"])

app.include_router(subscriptions.router, prefix="/api/v1", tags=["subscriptions"])

app.include_router(digests.router, prefix="/api/v1", tags=["digests"])


@app.on_event("startup")
async def startup_event():
    """Run application startup tasks."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Verify database connection
    db_health = await check_database()
    if db_health.status != "healthy":
        logger.warning(f"Database health check: {db_health.message}")
    else:
        logger.info("Database connection verified")

    # Verify Redis connection
    redis_health = await check_redis()
    if redis_health.status != "healthy":
        logger.warning(f"Redis health check: {redis_health.message}")
    else:
        logger.info("Redis connection verified")

    # Check Celery workers
    celery_health = await check_celery()
    logger.info(f"Celery status: {celery_health.message}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run application shutdown tasks."""
    logger.info(f"Shutting down {settings.APP_NAME}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
