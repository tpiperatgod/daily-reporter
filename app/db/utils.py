"""Database utility functions.

This module provides reusable database utilities to eliminate common
patterns across the codebase.
"""

from typing import Type, TypeVar, Optional, List, Tuple, Any
from uuid import UUID
from fastapi import HTTPException, status as http_status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def get_entity_or_404(
    session: AsyncSession,
    model: Type[T],
    entity_id: UUID,
    error_message: Optional[str] = None,
    eager_load: Optional[List] = None
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
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=message
        )
    
    return entity


async def paginate_query(
    session: AsyncSession,
    query,
    limit: int,
    offset: int
) -> Tuple[List, int]:
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
    additional_filters: Optional[List] = None
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


__all__ = [
    "get_entity_or_404",
    "paginate_query",
    "batch_check_exists",
]
