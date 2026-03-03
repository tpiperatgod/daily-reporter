"""Topic management API endpoints."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Topic, Item, Digest
from app.api.schemas import (
    TopicCreate,
    TopicUpdate,
    TopicResponse,
    TopicWithStats,
    PaginatedResponse,
    TriggerResponse,
)
from app.core.logging import get_logger
from app.db.utils import get_entity_or_404, paginate_query
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(topic_data: TopicCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new topic.

    Args:
        topic_data: Topic creation data
        db: Database session

    Returns:
        Created topic

    Raises:
        HTTPException: If validation fails
    """
    logger.info(f"Creating topic: {topic_data.name}")

    # Create topic
    topic = Topic(
        name=topic_data.name,
        query=topic_data.query,
        cron_expression=topic_data.cron_expression,
        is_enabled=True,
        last_tweet_id=topic_data.last_tweet_id,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)

    logger.info(f"Topic created: {topic.id}")
    return topic


@router.get("", response_model=PaginatedResponse)
async def list_topics(
    limit: int = 50,
    offset: int = 0,
    is_enabled: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all topics with pagination and filtering.

    Args:
        limit: Maximum number of topics to return
        offset: Number of topics to skip
        is_enabled: Filter by enabled status
        search: Search term for name or query
        db: Database session

    Returns:
        Paginated list of topics
    """
    query = select(Topic)

    # Apply filters
    if is_enabled is not None:
        query = query.where(Topic.is_enabled == is_enabled)

    if search:
        query = query.where((Topic.name.ilike(f"%{search}%")) | (Topic.query.ilike(f"%{search}%")))

    # Apply pagination
    query = query.order_by(Topic.created_at.desc())
    topics, total = await paginate_query(db, query, limit, offset)

    return PaginatedResponse.create(
        items=[TopicResponse.from_orm(t) for t in topics],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{topic_id}", response_model=TopicWithStats)
async def get_topic(topic_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get topic by ID with statistics.

    Args:
        topic_id: Topic UUID
        db: Database session

    Returns:
        Topic with statistics

    Raises:
        HTTPException: If topic not found
    """
    topic = await get_entity_or_404(db, Topic, topic_id)

    # Get statistics
    # Count items
    items_count = await db.execute(select(func.count(Item.id)).where(Item.topic_id == topic_id))
    total_items = items_count.scalar() or 0

    # Count digests
    digests_count = await db.execute(select(func.count(Digest.id)).where(Digest.topic_id == topic_id))
    total_digests = digests_count.scalar() or 0

    # Build response
    response = TopicWithStats.from_orm(topic)
    response.total_items = total_items
    response.total_digests = total_digests

    return response


@router.patch("/{topic_id}", response_model=TopicResponse)
async def update_topic(topic_id: UUID, topic_data: TopicUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update topic information.

    Args:
        topic_id: Topic UUID
        topic_data: Updated topic data
        db: Database session

    Returns:
        Updated topic

    Raises:
        HTTPException: If topic not found
    """
    topic = await get_entity_or_404(db, Topic, topic_id)

    # Update fields
    if topic_data.name is not None:
        topic.name = topic_data.name
    if topic_data.query is not None:
        topic.query = topic_data.query
    if topic_data.cron_expression is not None:
        topic.cron_expression = topic_data.cron_expression
    if topic_data.is_enabled is not None:
        topic.is_enabled = topic_data.is_enabled

    await db.commit()
    await db.refresh(topic)

    logger.info(f"Topic updated: {topic_id}")
    return topic


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(topic_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a topic.

    Args:
        topic_id: Topic UUID
        db: Database session

    Raises:
        HTTPException: If topic not found
    """
    topic = await get_entity_or_404(db, Topic, topic_id)

    await db.delete(topic)
    await db.commit()

    logger.info(f"Topic deleted: {topic_id}")


@router.post("/{topic_id}/trigger", response_model=TriggerResponse)
async def trigger_topic_collection(topic_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Manually trigger data collection for a topic.

    **DEPRECATED**: This endpoint is deprecated. Use POST /users/{user_id}/trigger
    for user-scoped aggregation instead.

    Args:
        topic_id: Topic UUID
        db: Database session

    Returns:
        Trigger response with task ID and deprecation warning

    Raises:
        HTTPException: If topic not found or not enabled
    """
    topic = await get_entity_or_404(db, Topic, topic_id)

    if not topic.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic is disabled. Enable it first.",
        )

    # Trigger Celery task
    task = celery_app.send_task("app.workers.tasks.collect_data", args=[str(topic_id)])

    logger.info(
        f"Manually triggered collection for topic {topic_id}",
        extra={"task_id": task.id},
    )

    return TriggerResponse(
        status="success",
        message="Data collection task triggered",
        task_id=task.id,
        topic_id=str(topic_id),
        deprecated=True,
        deprecation_message="Use POST /users/{user_id}/trigger for user-scoped aggregation",
    )
