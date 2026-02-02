"""User management API endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, Subscription
from app.api.schemas import (
    UserCreate,
    UserResponse,
    UserWithSubscriptions,
    SubscriptionResponse,
    PaginatedResponse
)
from app.core.logging import get_logger
from app.db.utils import get_entity_or_404, paginate_query

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user.

    Args:
        user_data: User creation data
        db: Database session

    Returns:
        Created user

    Raises:
        HTTPException: If email already exists
    """
    logger.info(f"Creating user with email: {user_data.email}")

    # Check if email already exists
    existing = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing.scalar_one_or_none():
        logger.warning(f"Email already exists: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Create user
    user = User(
        name=user_data.name,
        email=user_data.email,
        feishu_webhook_url=user_data.feishu_webhook_url,
        feishu_webhook_secret=user_data.feishu_webhook_secret
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User created: {user.id}")
    return user


@router.get("", response_model=PaginatedResponse)
async def list_users(
    limit: int = 50,
    offset: int = 0,
    search: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all users with pagination.

    Args:
        limit: Maximum number of users to return
        offset: Number of users to skip
        search: Search term for name or email
        db: Database session

    Returns:
        Paginated list of users
    """
    query = select(User)

    # Apply search filter
    if search:
        query = query.where(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    # Apply pagination
    query = query.order_by(User.created_at.desc())
    users, total = await paginate_query(db, query, limit, offset)

    return PaginatedResponse.create(
        items=[UserResponse.from_orm(u) for u in users],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{user_id}", response_model=UserWithSubscriptions)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID with subscriptions.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        User with subscriptions

    Raises:
        HTTPException: If user not found
    """
    user = await get_entity_or_404(db, User, user_id)

    # Load subscriptions
    subs_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    user.subscriptions = subs_result.scalars().all()

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update user information.

    Args:
        user_id: User UUID
        user_data: Updated user data
        db: Database session

    Returns:
        Updated user

    Raises:
        HTTPException: If user not found or email conflict
    """
    user = await get_entity_or_404(db, User, user_id)

    # Check email uniqueness if changing
    if user_data.email != user.email:
        existing = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        user.email = user_data.email

    # Update fields
    user.name = user_data.name
    user.feishu_webhook_url = user_data.feishu_webhook_url
    user.feishu_webhook_secret = user_data.feishu_webhook_secret

    await db.commit()
    await db.refresh(user)

    logger.info(f"User updated: {user_id}")
    return user
