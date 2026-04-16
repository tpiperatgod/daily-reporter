"""Mapping helpers from upstream payloads to normalized records."""

from __future__ import annotations

from twx.errors import TransformError
from twx.models import (
    NormalizedMedia,
    NormalizedMetrics,
    NormalizedTweet,
    NormalizedUser,
)


def normalize_tweet(raw: dict) -> NormalizedTweet:
    """Transform a raw tweet payload into a NormalizedTweet."""
    try:
        author = raw.get("author", {})
        return NormalizedTweet(
            id=str(raw["id"]),
            text=raw["text"],
            url=raw.get("url", f"https://x.com/{author.get('userName', '')}/status/{raw['id']}"),
            author_username=author.get("userName", ""),
            author_name=author.get("name"),
            created_at=parse_created_at(raw.get("createdAt", "")),
            metrics=extract_metrics(raw),
            media=extract_media(raw),
            is_retweet=bool(raw.get("retweetedTweet")),
            is_reply=bool(raw.get("isReply", raw.get("inReplyToStatus"))),
            is_quote=bool(raw.get("isQuoteStatus", raw.get("quoted_tweet"))),
        )
    except (KeyError, TypeError) as exc:
        raise TransformError(f"Failed to normalize tweet: {exc}") from exc


def normalize_user(raw: dict) -> NormalizedUser:
    """Transform a raw user payload into a NormalizedUser."""
    try:
        return NormalizedUser(
            username=raw.get("userName", ""),
            name=raw.get("name"),
            bio=raw.get("bio"),
            followers_count=int(raw.get("followersCount", 0)),
            following_count=int(raw.get("followingCount", 0)),
            tweet_count=int(raw.get("statusesCount", 0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TransformError(f"Failed to normalize user: {exc}") from exc


def parse_created_at(value: str) -> str:
    """Parse and normalize a createdAt timestamp to ISO 8601."""
    if not value:
        return ""
    # If already ISO-like, return as-is
    if "T" in value:
        return value
    # twitterapi.io sometimes returns format like "Mon Apr 15 10:30:00 +0000 2026"
    from datetime import datetime

    try:
        dt = datetime.strptime(value, "%a %b %d %H:%M:%S %z %Y")
        return dt.isoformat()
    except ValueError:
        return value


def extract_metrics(raw: dict) -> NormalizedMetrics:
    """Extract engagement metrics from a raw tweet."""
    return NormalizedMetrics(
        like_count=int(raw.get("likeCount", raw.get("likes", 0))),
        retweet_count=int(raw.get("retweetCount", raw.get("retweets", 0))),
        reply_count=int(raw.get("replyCount", raw.get("replies", 0))),
        view_count=int(raw.get("viewCount", raw.get("views", 0))),
        bookmark_count=int(raw.get("bookmarkCount", raw.get("bookmarks", 0))),
    )


def extract_media(raw: dict) -> list[NormalizedMedia]:
    """Extract media attachments from a raw tweet."""
    media_list = raw.get("media", [])
    if not isinstance(media_list, list):
        return []
    result = []
    for item in media_list:
        if not isinstance(item, dict):
            continue
        media_type = item.get("type", "photo")
        url = item.get("url", "")
        alt_text = item.get("alt_text", "")
        if url:
            result.append(NormalizedMedia(type=media_type, url=url, alt_text=alt_text))
        # Also check for media_url (some payloads use different keys)
        elif item.get("media_url"):
            result.append(NormalizedMedia(type=media_type, url=item["media_url"], alt_text=alt_text))
    return result
