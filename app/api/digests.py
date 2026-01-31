"""Digest history API endpoints."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from app.db.session import get_db
from app.db.models import Digest, Delivery, Topic
from app.api.schemas import (
    DigestResponse,
    DigestWithDetails,
    PaginatedResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/digests", tags=["digests"])


@router.get("", response_model=PaginatedResponse)
async def list_digests(
    limit: int = 50,
    offset: int = 0,
    topic_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
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

    # Get total count
    count_result = await db.execute(
        select(func.count(Digest.id)).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Apply pagination with eager loading
    query = query.options(
        selectinload(Digest.topic)
    ).order_by(Digest.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    digests = result.scalars().all()

    return PaginatedResponse.create(
        items=[DigestResponse.from_orm(d) for d in digests],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{digest_id}", response_model=DigestWithDetails)
async def get_digest(
    digest_id: UUID,
    db: AsyncSession = Depends(get_db)
):
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
    result = await db.execute(
        select(Digest)
        .options(
            selectinload(Digest.topic),
            selectinload(Digest.deliveries)
        )
        .where(Digest.id == digest_id)
    )
    digest = result.scalar_one_or_none()

    if not digest:
        logger.warning(f"Digest not found: {digest_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Digest not found"
        )

    return digest


@router.get("/{digest_id}/deliveries", response_model=PaginatedResponse)
async def get_digest_deliveries(
    digest_id: UUID,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
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
    digest_result = await db.execute(
        select(Digest).where(Digest.id == digest_id)
    )
    digest = digest_result.scalar_one_or_none()
    if not digest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Digest not found"
        )

    # Query deliveries
    query = select(Delivery).where(Delivery.digest_id == digest_id)

    # Apply status filter
    if status:
        query = query.where(Delivery.status == status)

    # Get total count
    count_result = await db.execute(
        select(func.count(Delivery.id)).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Apply pagination
    query = query.order_by(Delivery.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    deliveries = result.scalars().all()

    return PaginatedResponse.create(
        items=deliveries,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{digest_id}/content")
async def get_digest_content(
    digest_id: UUID,
    db: AsyncSession = Depends(get_db)
):
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
    result = await db.execute(
        select(Digest).where(Digest.id == digest_id)
    )
    digest = result.scalar_one_or_none()

    if not digest:
        logger.warning(f"Digest not found: {digest_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Digest not found"
        )

    return {
        "digest_id": str(digest.id),
        "content": digest.rendered_content,
        "content_type": "text/markdown"
    }
