"""Shared notification delivery service.

This module provides reusable functionality for sending digest notifications
to users. It is used by both the API endpoint (manual sends) and the Celery
task (automated sends).
"""

from datetime import datetime, UTC
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.config import settings
from app.db.models import Digest, User, Delivery
from app.services.notifier.feishu import FeishuNotifier
from app.services.notifier.email import EmailNotifier
from app.services.llm.client import DigestResult

logger = get_logger(__name__)


async def send_digest_to_user(
    digest: Digest,
    user: User,
    channels: List[str],
    session: AsyncSession
) -> List[Delivery]:
    """
    Send digest to user via specified channels and create delivery records.

    This function handles the actual notification sending and delivery tracking
    for a single user. It creates delivery records, attempts to send notifications
    through the specified channels, and updates delivery status accordingly.

    Args:
        digest: Digest object (with topic eager loaded)
        user: User object
        channels: List of channel names ("feishu", "email")
        session: Database session for creating delivery records

    Returns:
        List of created Delivery records with updated status

    Raises:
        Exception: Individual channel failures are caught and logged but don't
                   stop the function. Status is set to "failed" in delivery record.
    """
    feishu_notifier = FeishuNotifier(log_only=False)
    email_notifier = EmailNotifier(log_only=settings.EMAIL_LOG_ONLY)

    deliveries = []

    for channel in channels:
        # Create delivery record
        delivery = Delivery(
            digest_id=str(digest.id),
            user_id=str(user.id),
            channel=channel,
            status="pending"
        )
        session.add(delivery)
        await session.flush()  # Get delivery ID

        # Send notification
        try:
            if channel == "feishu":
                if not user.feishu_webhook_url:
                    raise ValueError("No Feishu webhook URL configured")

                # Parse DigestResult from summary_json
                digest_result = DigestResult(**digest.summary_json)

                await feishu_notifier.send(
                    webhook_url=user.feishu_webhook_url,
                    digest_result=digest_result,
                    topic_name=digest.topic.name,
                    webhook_secret=user.feishu_webhook_secret if hasattr(user, 'feishu_webhook_secret') else None
                )

            elif channel == "email":
                await email_notifier.send(
                    to_email=user.email,
                    subject=f"Digest: {digest.topic.name}",
                    content=digest.rendered_content
                )

            # Update delivery status
            delivery.status = "success"
            delivery.sent_at = datetime.now(UTC)

            logger.info(
                f"Sent {channel} notification to {user.email}",
                extra={
                    "channel": channel,
                    "user_id": str(user.id),
                    "delivery_id": str(delivery.id),
                    "digest_id": str(digest.id)
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to send {channel} notification to {user.email}: {e}",
                extra={
                    "channel": channel,
                    "user_id": str(user.id),
                    "digest_id": str(digest.id)
                }
            )
            delivery.status = "failed"
            delivery.error_msg = str(e)
            delivery.retry_count += 1

        deliveries.append(delivery)

    return deliveries


__all__ = ["send_digest_to_user"]
