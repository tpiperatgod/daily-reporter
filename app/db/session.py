from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from celery.signals import worker_process_init
from app.core.config import settings

# Global variables (initially None, initialized per worker process)
engine = None
AsyncSessionLocal = None


def init_db():
    """
    Initialize database engine and session factory.

    This function is called:
    1. When Celery worker process starts (via worker_process_init signal)
    2. As fallback in get_db() for non-Celery contexts (FastAPI dev mode)
    """
    global engine, AsyncSessionLocal

    if engine is not None:
        return  # Already initialized

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,  # Disable pooling to prevent event loop mismatch with asyncio.run()
    )

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def ensure_session_initialized():
    """
    Ensure AsyncSessionLocal is initialized.

    This is needed because worker_process_init signal doesn't fire
    with --pool=solo, which is used in local development.
    """
    if AsyncSessionLocal is None:
        init_db()


def get_async_session_local():
    """
    Get AsyncSessionLocal session maker, ensuring it's initialized.

    This function must be used instead of directly importing AsyncSessionLocal
    in contexts where the session might not be initialized at import time
    (e.g., Celery tasks with solo pool).

    Returns:
        async_sessionmaker: The initialized session maker
    """
    ensure_session_initialized()
    return AsyncSessionLocal


@worker_process_init.connect
def init_worker(**kwargs):
    """
    Initialize DB when Celery worker process starts.

    Creates a shared engine with NullPool to ensure each database operation
    gets a fresh connection in the current event loop context, preventing
    'attached to a different loop' errors when using asyncio.run() in tasks.
    """
    init_db()


async def get_db() -> AsyncSession:
    """
    Dependency function to get database session.

    Yields:
        AsyncSession: Database session
    """
    # Fallback for non-Celery contexts (FastAPI dev mode)
    if AsyncSessionLocal is None:
        init_db()

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
