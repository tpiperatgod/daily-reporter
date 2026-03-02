"""Shared notification delivery service.

This module provides reusable functionality for sending digest notifications
to users. It is used by both the API endpoint (manual sends) and the Celery
task (automated sends).
"""

from datetime import datetime, UTC
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.core.config import settings
from app.core.constants import DeliveryStatus, NotificationChannel
from app.db.models import Digest, User, Delivery, UserDigest
from app.services.notifier.feishu import FeishuNotifier
from app.services.notifier.email import EmailNotifier
from app.services.llm.client import DigestResult

logger = get_logger(__name__)


async def send_digest_to_user(
    user: User,
    channels: List[str],
    session: AsyncSession,
    digest: Optional[Digest] = None,
    user_digest: Optional[UserDigest] = None,
    idempotent: bool = False,
) -> List[Delivery]:
    """
    Send digest to user via specified channels and create delivery records.

    This function handles the actual notification sending and delivery tracking
    for a single user. It creates delivery records, attempts to send notifications
    through the specified channels, and updates delivery status accordingly.

    Args:
        user: User object
        channels: List of channel names ("feishu", "email")
        session: Database session for creating delivery records
        digest: Topic-scoped Digest object (mutually exclusive with user_digest)
        user_digest: User-scoped UserDigest object (mutually exclusive with digest)
        idempotent: If True, reuse existing delivery records instead of creating new ones
                    (prevents duplicates on retry). Default: False.

    Returns:
        List of created/reused Delivery records with updated status

    Raises:
        ValueError: If neither or both digest types are provided
        Exception: Individual channel failures are caught and logged but don't
                   stop the function. Status is set to "failed" in delivery record.
    """
    # Validate mutually exclusive parameters
    if not digest and not user_digest:
        raise ValueError("Either digest or user_digest must be provided")
    if digest and user_digest:
        raise ValueError("Cannot provide both digest and user_digest")

    feishu_notifier = FeishuNotifier(log_only=False)
    email_notifier = EmailNotifier(log_only=settings.EMAIL_LOG_ONLY)

    deliveries = []

    # Determine digest info for notifications
    if digest:
        digest_id = str(digest.id)
        user_digest_id = None
        topic_name = digest.topic.name
        digest_result = DigestResult(**digest.summary_json)
        rendered_content = digest.rendered_content
    else:
        digest_id = None
        user_digest_id = str(user_digest.id)
        topic_name = "User Digest"
        digest_result = DigestResult(**user_digest.summary_json)
        rendered_content = user_digest.rendered_content

    for channel in channels:
        # Create or reuse delivery record
        if idempotent:
            # Check for existing delivery to prevent duplicates on retry
            existing_result = await session.execute(
                select(Delivery).where(
                    and_(
                        Delivery.digest_id == digest_id,
                        Delivery.user_digest_id == user_digest_id,
                        Delivery.user_id == str(user.id),
                        Delivery.channel == channel,
                    )
                )
            )
            delivery = existing_result.scalar_one_or_none()

            if delivery:
                logger.info(
                    f"Reusing existing delivery {delivery.id} for {channel}",
                    extra={"delivery_id": str(delivery.id), "channel": channel},
                )
            else:
                # Create new delivery if none exists
                delivery = Delivery(
                    digest_id=digest_id,
                    user_digest_id=user_digest_id,
                    user_id=str(user.id),
                    channel=channel,
                    status=DeliveryStatus.PENDING,
                )
                session.add(delivery)
                await session.flush()
        else:
            # Always create new delivery (non-idempotent)
            delivery = Delivery(
                digest_id=digest_id,
                user_digest_id=user_digest_id,
                user_id=str(user.id),
                channel=channel,
                status=DeliveryStatus.PENDING,
            )
            session.add(delivery)
            await session.flush()  # Get delivery ID
        try:
            if channel == NotificationChannel.FEISHU:
                if not user.feishu_webhook_url:
                    raise ValueError("No Feishu webhook URL configured")

                await feishu_notifier.send(
                    webhook_url=user.feishu_webhook_url,
                    digest_result=digest_result,
                    topic_name=topic_name,
                    webhook_secret=user.feishu_webhook_secret if hasattr(user, "feishu_webhook_secret") else None,
                )

            elif channel == NotificationChannel.EMAIL:
                await email_notifier.send(
                    to_email=user.email,
                    subject=f"Digest: {topic_name}",
                    content=rendered_content,
                )
            # Update delivery status
            delivery.status = DeliveryStatus.SUCCESS
            delivery.sent_at = datetime.now(UTC)

            logger.info(
                f"Sent {channel} notification to {user.email}",
                extra={
                    "channel": channel,
                    "user_id": str(user.id),
                    "delivery_id": str(delivery.id),
                    "digest_id": digest_id,
                    "user_digest_id": user_digest_id,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to send {channel} notification to {user.email}: {e}",
                extra={
                    "channel": channel,
                    "user_id": str(user.id),
                    "digest_id": digest_id,
                    "user_digest_id": user_digest_id,
                },
            )
            delivery.status = DeliveryStatus.FAILED
            delivery.error_msg = str(e)
            delivery.retry_count += 1
        deliveries.append(delivery)

    return deliveries


__all__ = ["send_digest_to_user"]
