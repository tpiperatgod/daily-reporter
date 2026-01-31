"""Feishu notification service.

For development, this logs the notification content instead of
sending actual webhook calls.
"""

import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FeishuNotifier:
    """
    Service for sending notifications to Feishu (Lark) webhooks.

    In development mode (LOG_ONLY=true), logs instead of sending.
    """

    def __init__(self, log_only: bool = True):
        """
        Initialize Feishu notifier.

        Args:
            log_only: If True, log instead of sending (for development)
        """
        self.log_only = log_only
        if not log_only:
            self.client = httpx.AsyncClient(timeout=30.0)

    async def send(self, webhook_url: str, title: str, content: str):
        """
        Send a notification to Feishu.

        Args:
            webhook_url: Feishu webhook URL
            title: Notification title
            content: Markdown content

        Raises:
            Exception: If sending fails
        """
        if self.log_only:
            # Development mode: log instead of sending
            logger.info(
                f"[Feishu - LOG MODE] Would send notification",
                extra={
                    "webhook_url": webhook_url[:50] + "..." if len(webhook_url) > 50 else webhook_url,
                    "title": title,
                    "content_length": len(content),
                    "content_preview": content[:200] + "..." if len(content) > 200 else content
                }
            )
            return

        # Production mode: send actual webhook
        try:
            # Build Feishu card message
            card = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": title
                        }
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": content
                            }
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "plain_text",
                                "content": f"Sent at: {self._get_timestamp()}"
                            }
                        }
                    ]
                }
            }

            # Send webhook
            response = await self.client.post(webhook_url, json=card)
            response.raise_for_status()

            logger.info(
                f"Feishu notification sent successfully",
                extra={
                    "webhook_url": webhook_url[:50],
                    "title": title
                }
            )

        except Exception as e:
            logger.error(f"Failed to send Feishu notification: {e}")
            raise

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    async def close(self):
        """Close the HTTP client."""
        if not self.log_only and hasattr(self, 'client'):
            await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
