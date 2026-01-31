"""Subscription management API endpoints."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Subscription, Topic, User
from app.api.schemas import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionWithDetails,
    PaginatedResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    sub_data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new subscription.

    Args:
        sub_data: Subscription creation data
        db: Database session

    Returns:
        Created subscription

    Raises:
        HTTPException: If user/topic not found or already subscribed
    """
    logger.info(
        f"Creating subscription: user={sub_data.user_id}, topic={sub_data.topic_id}"
    )

    # Verify user exists
    user_result = await db.execute(
        select(User).where(User.id == sub_data.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify topic exists
    topic_result = await db.execute(
        select(Topic).where(Topic.id == sub_data.topic_id)
    )
    topic = topic_result.scalar_one_or_none()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )

    # Check if subscription already exists
    existing_result = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.user_id == sub_data.user_id,
                Subscription.topic_id == sub_data.topic_id
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already subscribed to this topic"
        )

    # Create subscription
    subscription = Subscription(
        user_id=sub_data.user_id,
        topic_id=sub_data.topic_id,
        enable_feishu=sub_data.enable_feishu,
        enable_email=sub_data.enable_email
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    logger.info(f"Subscription created: {subscription.id}")
    return subscription


@router.get("", response_model=PaginatedResponse)
async def list_subscriptions(
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[UUID] = None,
    topic_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List subscriptions with pagination and filtering.

    Args:
        limit: Maximum number of subscriptions to return
        offset: Number of subscriptions to skip
        user_id: Filter by user ID
        topic_id: Filter by topic ID
        db: Database session

    Returns:
        Paginated list of subscriptions
    """
    query = select(Subscription)

    # Apply filters
    if user_id:
        query = query.where(Subscription.user_id == user_id)
    if topic_id:
        query = query.where(Subscription.topic_id == topic_id)

    # Get total count
    count_result = await db.execute(
        select(func.count(Subscription.id)).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Apply pagination with eager loading
    query = query.options(
        selectinload(Subscription.user),
        selectinload(Subscription.topic)
    ).order_by(Subscription.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    subscriptions = result.scalars().all()

    return PaginatedResponse.create(
        items=[SubscriptionResponse.from_orm(s) for s in subscriptions],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{subscription_id}", response_model=SubscriptionWithDetails)
async def get_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscription by ID with details.

    Args:
        subscription_id: Subscription UUID
        db: Database session

    Returns:
        Subscription with user and topic details

    Raises:
        HTTPException: If subscription not found
    """
    result = await db.execute(
        select(Subscription)
        .options(
            selectinload(Subscription.user),
            selectinload(Subscription.topic)
        )
        .where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        logger.warning(f"Subscription not found: {subscription_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    return subscription


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    sub_data: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update subscription preferences.

    Args:
        subscription_id: Subscription UUID
        sub_data: Updated subscription data
        db: Database session

    Returns:
        Updated subscription

    Raises:
        HTTPException: If subscription not found
    """
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        logger.warning(f"Subscription not found: {subscription_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    # Update fields
    if sub_data.enable_feishu is not None:
        subscription.enable_feishu = sub_data.enable_feishu
    if sub_data.enable_email is not None:
        subscription.enable_email = sub_data.enable_email

    await db.commit()
    await db.refresh(subscription)

    logger.info(f"Subscription updated: {subscription_id}")
    return subscription


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a subscription.

    Args:
        subscription_id: Subscription UUID
        db: Database session

    Raises:
        HTTPException: If subscription not found
    """
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        logger.warning(f"Subscription not found: {subscription_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    await db.delete(subscription)
    await db.commit()

    logger.info(f"Subscription deleted: {subscription_id}")
