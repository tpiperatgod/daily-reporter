"""Digest history API endpoints."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Digest, Delivery, User
from app.api.schemas import (
    DigestWithDetails,
    PaginatedResponse,
    SendDigestRequest,
    SendDigestResponse,
    SendDigestDelivery,
)
from app.core.logging import get_logger
from app.core.constants import NotificationChannel, DeliveryStatus
from app.db.utils import get_entity_or_404, paginate_query

logger = get_logger(__name__)

router = APIRouter(prefix="/digests", tags=["digests"])


@router.get("", response_model=PaginatedResponse)
async def list_digests(
    limit: int = 50,
    offset: int = 0,
    topic_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List digests with pagination and filtering.

    Args:
        limit: Maximum number of digests to return
        offset: Number of digests to skip
        topic_id: Filter by topic ID
        db: Database session

    Returns:
        Paginated list of digests
    """
    query = select(Digest)

    # Apply filters
    if topic_id:
        query = query.where(Digest.topic_id == topic_id)

    # Apply pagination with eager loading
    query = query.options(selectinload(Digest.topic), selectinload(Digest.deliveries)).order_by(
        Digest.created_at.desc()
    )

    digests, total = await paginate_query(db, query, limit, offset)

    return PaginatedResponse.create(
        items=[DigestWithDetails.from_orm(d) for d in digests],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{digest_id}", response_model=DigestWithDetails)
async def get_digest(digest_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get digest by ID with details.

    Args:
        digest_id: Digest UUID
        db: Database session

    Returns:
        Digest with topic and delivery details

    Raises:
        HTTPException: If digest not found
    """
    digest = await get_entity_or_404(
        db,
        Digest,
        digest_id,
        eager_load=[selectinload(Digest.topic), selectinload(Digest.deliveries)],
    )

    return digest


@router.get("/{digest_id}/deliveries", response_model=PaginatedResponse)
async def get_digest_deliveries(
    digest_id: UUID,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get delivery records for a digest.

    Args:
        digest_id: Digest UUID
        limit: Maximum number of deliveries to return
        offset: Number of deliveries to skip
        status: Filter by delivery status
        db: Database session

    Returns:
        Paginated list of deliveries

    Raises:
        HTTPException: If digest not found
    """
    # Verify digest exists
    await get_entity_or_404(db, Digest, digest_id)

    # Query deliveries
    query = select(Delivery).where(Delivery.digest_id == digest_id)

    # Apply status filter
    if status:
        query = query.where(Delivery.status == status)

    # Apply pagination
    query = query.order_by(Delivery.created_at.desc())
    deliveries, total = await paginate_query(db, query, limit, offset)

    return PaginatedResponse.create(items=deliveries, total=total, limit=limit, offset=offset)


@router.get("/{digest_id}/content")
async def get_digest_content(digest_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get the rendered markdown content of a digest.

    Args:
        digest_id: Digest UUID
        db: Database session

    Returns:
        Markdown content

    Raises:
        HTTPException: If digest not found
    """
    digest = await get_entity_or_404(db, Digest, digest_id)

    return {
        "digest_id": str(digest.id),
        "content": digest.rendered_content,
        "content_type": "text/markdown",
    }


@router.post(
    "/{digest_id}/send",
    response_model=SendDigestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_digest(digest_id: UUID, request: SendDigestRequest, db: AsyncSession = Depends(get_db)):
    """
    Manually send a digest to a specific user.

    This endpoint allows on-demand delivery of a digest outside the automated
    notification workflow. It respects the user's channel preferences
    (enable_feishu, enable_email) and creates new delivery records for tracking.

    Args:
        digest_id: UUID of the digest to send
        request: Request body with user_id
        db: Database session

    Returns:
        SendDigestResponse with delivery results

    Raises:
        HTTPException:
            - 404 if digest or user not found
            - 400 if no channels enabled or user missing required config
    """
    from app.services.notifier.delivery import send_digest_to_user

    # 1. Load digest with topic (eager loading)
    digest_result = await db.execute(select(Digest).options(selectinload(Digest.topic)).where(Digest.id == digest_id))
    digest = digest_result.scalar_one_or_none()

    if not digest:
        logger.warning(f"Digest not found: {digest_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digest not found")

    # 2. Load user with eager loading
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found: {request.user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 3. Determine channels from user settings
    channels = []
    if user.enable_feishu:
        channels.append(NotificationChannel.FEISHU)
    if user.enable_email:
        channels.append(NotificationChannel.EMAIL)

    if not channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No channels enabled for user",
        )

    # 4. Validate user configurations
    if NotificationChannel.FEISHU in channels and not user.feishu_webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has Feishu enabled but no webhook URL configured",
        )

    # 5. Send notifications and create delivery records
    logger.info(
        f"Manually sending digest {digest_id} to user {request.user_id}",
        extra={
            "digest_id": str(digest_id),
            "user_id": str(user.id),
            "channels": channels,
        },
    )

    deliveries = await send_digest_to_user(user=user, channels=channels, session=db, digest=digest)
    await db.commit()

    # 6. Build response
    successful = sum(1 for d in deliveries if d.status == DeliveryStatus.SUCCESS)
    failed = sum(1 for d in deliveries if d.status == DeliveryStatus.FAILED)

    logger.info(
        f"Digest sent: {successful} successful, {failed} failed",
        extra={
            "digest_id": str(digest_id),
            "user_id": str(request.user_id),
            "successful": successful,
            "failed": failed,
        },
    )

    return SendDigestResponse(
        digest_id=digest_id,
        user_id=request.user_id,
        deliveries=[SendDigestDelivery.from_orm(d) for d in deliveries],
        total_sent=len(deliveries),
        successful=successful,
        failed=failed,
    )
