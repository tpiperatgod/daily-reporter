"""Database utility functions.

This module provides reusable database utilities to eliminate common
patterns across the codebase.
"""

from typing import Type, TypeVar, Optional, List, Tuple, Any
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status as http_status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Item

logger = get_logger(__name__)

T = TypeVar("T")


async def get_entity_or_404(
    session: AsyncSession,
    model: Type[T],
    entity_id: UUID,
    error_message: Optional[str] = None,
    eager_load: Optional[List] = None,
) -> T:
    """
    Get entity by ID or raise 404.

    This utility eliminates the repetitive pattern of:
    - Execute select query
    - Check if result is None
    - Log warning
    - Raise HTTPException

    Args:
        session: Database session
        model: SQLAlchemy model class
        entity_id: UUID of entity to fetch
        error_message: Custom error message (defaults to "{Model} not found")
        eager_load: List of relationships to eager load (e.g., [Model.relationship])

    Returns:
        The fetched entity

    Raises:
        HTTPException: 404 if entity not found

    Example:
        user = await get_entity_or_404(db, User, user_id)
        # Instead of:
        # result = await db.execute(select(User).where(User.id == user_id))
        # user = result.scalar_one_or_none()
        # if not user:
        #     raise HTTPException(status_code=404, detail="User not found")
    """
    query = select(model).where(model.id == entity_id)

    if eager_load:
        query = query.options(*eager_load)

    result = await session.execute(query)
    entity = result.scalar_one_or_none()

    if not entity:
        entity_name = model.__name__
        message = error_message or f"{entity_name} not found"
        logger.warning(f"{entity_name} not found: {entity_id}")
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=message)

    return entity


async def paginate_query(session: AsyncSession, query, limit: int, offset: int) -> Tuple[List, int]:
    """
    Apply pagination and return (items, total).

    This utility eliminates the repetitive pattern of:
    - Count query with subquery
    - Apply limit/offset
    - Execute and fetch results

    Args:
        session: Database session
        query: SQLAlchemy select query (before pagination)
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        Tuple of (items, total_count)

    Example:
        query = select(User).where(User.name.ilike(f"%{search}%"))
        users, total = await paginate_query(db, query, limit, offset)
        # Instead of:
        # count_result = await db.execute(select(func.count(...)).select_from(query.subquery()))
        # total = count_result.scalar()
        # query = query.limit(limit).offset(offset)
        # result = await db.execute(query)
        # users = result.scalars().all()
    """
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    paginated_query = query.limit(limit).offset(offset)
    result = await session.execute(paginated_query)
    items = result.scalars().all()

    return items, total


async def batch_check_exists(
    session: AsyncSession,
    model: Type[T],
    column,
    values: List[Any],
    additional_filters: Optional[List] = None,
) -> set:
    """
    Check which values exist using single IN query.

    This is critical for fixing N+1 query problems in deduplication logic.
    Instead of checking each value individually (N queries), this uses a
    single query with IN clause.

    Args:
        session: Database session
        model: SQLAlchemy model class
        column: Column to check (e.g., Item.source_id)
        values: List of values to check
        additional_filters: Optional list of additional filter conditions

    Returns:
        Set of values that exist in the database

    Example:
        # Check which source_ids already exist
        source_ids = ["id1", "id2", "id3", ...]
        existing = await batch_check_exists(
            session, Item, Item.source_id, source_ids,
            additional_filters=[Item.topic_id == topic_id]
        )
        # Returns: {"id1", "id3"} (if only these exist)

        # Now check in memory:
        for source_id in source_ids:
            if source_id in existing:
                # Skip duplicate
                continue
    """
    if not values:
        return set()

    query = select(column).where(column.in_(values))

    if additional_filters:
        for filter_condition in additional_filters:
            query = query.where(filter_condition)

    result = await session.execute(query)
    return set(result.scalars().all())


async def fetch_items_for_user_topics(
    session: AsyncSession,
    topic_ids: List[UUID],
    start_date: datetime,
    end_date: datetime,
    limit: int = 500,
) -> List[Item]:
    """
    Fetch candidate items across subscribed topic IDs with deterministic ordering.

    This function queries items from multiple topics within a time window,
    deduplicates by source_id globally (not per-topic), and returns them
    ordered by created_at DESC.

    This is used for user-level aggregation where a user subscribes to
    multiple topics and needs a unified, deduplicated feed of items.

    Args:
        session: Database session
        topic_ids: List of topic UUIDs to fetch items from
        start_date: Start of time window (inclusive)
        end_date: End of time window (inclusive)
        limit: Maximum number of items to return (default: 500)

    Returns:
        List of Item objects ordered by created_at DESC, deduplicated by source_id

    Example:
        # Fetch items from user's subscribed topics
        from datetime import datetime, timedelta, UTC
        from uuid import UUID

        topic_ids = [UUID("..."), UUID("...")]
        start = datetime.now(UTC) - timedelta(days=1)
        end = datetime.now(UTC)

        items = await fetch_items_for_user_topics(
            session, topic_ids, start, end, limit=500
        )
        # Returns items from all topics, deduped by source_id
    """
    if not topic_ids:
        return []

    # Query items from multiple topics within time window
    query = (
        select(Item)
        .where(
            and_(
                Item.topic_id.in_(topic_ids),
                Item.created_at >= start_date,
                Item.created_at <= end_date,
            )
        )
        .order_by(Item.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    items = result.scalars().all()

    # Deduplicate by source_id globally (keep first occurrence)
    # Since source_id has a UNIQUE constraint in DB, duplicates shouldn't exist
    # but we dedupe in Python as a safety measure and to ensure deterministic output
    seen_source_ids = set()
    unique_items = []

    for item in items:
        if item.source_id not in seen_source_ids:
            seen_source_ids.add(item.source_id)
            unique_items.append(item)

    return unique_items

__all__ = [
    "get_entity_or_404",
    "paginate_query",
    "batch_check_exists",
    "fetch_items_for_user_topics",
]

