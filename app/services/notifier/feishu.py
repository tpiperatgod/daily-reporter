"""Feishu notification service.

For development, this logs the notification content instead of
sending actual webhook calls.
"""

import time
import hmac
import hashlib
import base64
from typing import Optional, Dict, Any
import httpx
from app.core.logging import get_logger
from app.services.llm.client import DigestResult

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

    def _gen_sign(self, timestamp: int, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook security."""
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign

    def _format_number(self, num: float) -> str:
        """Format numbers with K/M suffixes (e.g., 53807.5 -> 53.8K)."""
        if num >= 1000000:
            return f"{num / 1000000:.1f}M"
        if num >= 1000:
            return f"{num / 1000:.1f}K"
        return f"{int(num)}"

    def _get_sentiment_color(self, sentiment: str) -> str:
        """Map sentiment to Feishu card header color."""
        mapping = {
            "positive": "green",
            "negative": "red",
            "mixed": "orange",
            "neutral": "grey",
        }
        return mapping.get(sentiment.lower(), "blue")

    def _build_rich_card(self, digest_result: DigestResult, topic_name: str) -> Dict[str, Any]:
        """
        Build Feishu rich interactive card from DigestResult.

        Based on design from demos/feishu-api.md.
        """
        stats = digest_result.stats
        highlights = digest_result.highlights

        # 1. Statistics dashboard (multi-column layout with fields)
        stats_fields = [
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**Total Posts**\n{stats.total_posts_analyzed}",
                },
            },
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**Engagement**\n{self._format_number(stats.total_engagement)}",
                },
            },
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**Authors**\n{stats.unique_authors}",
                },
            },
            {
                "is_short": True,
                "text": {
                    "tag": "lark_md",
                    "content": f"**Avg/Post**\n{self._format_number(stats.avg_engagement_per_post)}",
                },
            },
        ]

        # 2. Theme tags
        theme_str = "  ".join([f"🏷️ {theme}" for theme in digest_result.themes])

        # 3. Build elements list
        elements = [
            # Statistics module
            {"tag": "div", "fields": stats_fields},
            {"tag": "hr"},  # Separator
            # Themes module
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**Themes:**\n{theme_str}"},
            },
        ]

        # 4. Add highlights with dynamic score icons
        for idx, highlight in enumerate(highlights):
            # Score-based icon
            score_icon = "🔥" if highlight.score >= 9 else "⭐" if highlight.score >= 7 else "📝"

            # Build source links
            links_md = [f"[Source {i + 1}]({url})" for i, url in enumerate(highlight.representative_urls)]
            links_str = " | ".join(links_md)

            # Formatted highlight text
            summary_text = (
                f"{score_icon} **{highlight.title}** (Score: {highlight.score})\n{highlight.summary}\n🔗 {links_str}"
            )

            # Add separator before first highlight
            if idx == 0:
                elements.append({"tag": "hr"})

            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": summary_text}})

        # 5. Footer with metadata
        elements.append(
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"Generated for {topic_name} • Powered by AI Digest",
                    }
                ],
            }
        )

        # 6. Assemble final card
        card = {
            "config": {"wide_screen_mode": True},  # Enable wide screen
            "header": {
                "template": self._get_sentiment_color(digest_result.sentiment),
                "title": {"tag": "plain_text", "content": digest_result.headline},
            },
            "elements": elements,
        }

        return card

    async def send(
        self,
        webhook_url: str,
        digest_result: DigestResult,
        topic_name: str,
        webhook_secret: Optional[str] = None,
    ):
        """
        Send rich card notification to Feishu webhook.

        Args:
            webhook_url: Feishu webhook URL
            digest_result: DigestResult with headline, sentiment, themes, highlights, stats
            topic_name: Topic name for footer
            webhook_secret: Optional webhook secret for HMAC signature

        Raises:
            Exception: If sending fails
        """
        if self.log_only:
            # Development mode: log instead of sending
            logger.info(
                "[Feishu - LOG MODE] Would send rich card",
                extra={
                    "webhook_url": webhook_url[:50] + "..." if len(webhook_url) > 50 else webhook_url,
                    "headline": digest_result.headline,
                    "sentiment": digest_result.sentiment,
                    "highlights_count": len(digest_result.highlights),
                    "themes": digest_result.themes,
                },
            )
            return

        # Production mode: send actual webhook
        try:
            # Build rich card
            card_content = self._build_rich_card(digest_result, topic_name)

            # Prepare payload
            current_ts = int(time.time())
            payload = {
                "timestamp": current_ts,
                "msg_type": "interactive",
                "card": card_content,
            }

            # Add signature if secret provided
            if webhook_secret:
                payload["sign"] = self._gen_sign(current_ts, webhook_secret)

            # Send webhook
            response = await self.client.post(webhook_url, json=payload)
            response.raise_for_status()

            logger.info(
                "Feishu rich card sent successfully",
                extra={
                    "webhook_url": webhook_url[:50],
                    "headline": digest_result.headline,
                    "sentiment": digest_result.sentiment,
                },
            )

        except Exception as e:
            logger.error(f"Failed to send Feishu notification: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        if not self.log_only and hasattr(self, "client"):
            await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
