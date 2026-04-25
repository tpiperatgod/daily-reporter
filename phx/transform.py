"""Normalize Product Hunt GraphQL payloads into phx models."""

from __future__ import annotations

from typing import Any

from phx.errors import TransformError
from phx.models import MakerRef, MediaRef, NormalizedLaunch, ProductDetail, ProductLinkRef, TopicRef


def _require(raw: dict, key: str) -> Any:
    if key not in raw:
        raise TransformError(f"missing required field: {key}")
    return raw[key]


def _as_int(value: Any, *, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def _thumbnail_url(raw: dict) -> str | None:
    thumbnail = raw.get("thumbnail")
    if not isinstance(thumbnail, dict):
        return None
    return thumbnail.get("url")


def _topic_nodes(raw: dict) -> list[dict]:
    topics = raw.get("topics")
    if not isinstance(topics, dict):
        return []
    nodes = topics.get("nodes")
    if not isinstance(nodes, list):
        return []
    return [node for node in nodes if isinstance(node, dict)]


def _makers(raw: dict) -> list[dict]:
    makers = raw.get("makers")
    if not isinstance(makers, list):
        return []
    return [maker for maker in makers if isinstance(maker, dict)]


def _media_items(raw: dict) -> list[dict]:
    media = raw.get("media")
    if not isinstance(media, list):
        return []
    return [item for item in media if isinstance(item, dict) and item.get("url")]


def _product_links(raw: dict) -> list[dict]:
    links = raw.get("productLinks")
    if not isinstance(links, list):
        return []
    return [link for link in links if isinstance(link, dict) and link.get("url")]


def normalize_launch(raw: dict) -> NormalizedLaunch:
    if not isinstance(raw, dict):
        raise TransformError(f"expected dict, got {type(raw).__name__}")
    try:
        return NormalizedLaunch(
            id=str(_require(raw, "id")),
            slug=str(_require(raw, "slug")),
            name=str(_require(raw, "name")),
            tagline=raw.get("tagline"),
            description=raw.get("description"),
            product_hunt_url=str(_require(raw, "url")),
            website_url=raw.get("website"),
            thumbnail_url=_thumbnail_url(raw),
            votes_count=_as_int(raw.get("votesCount")),
            comments_count=_as_int(raw.get("commentsCount")),
            topics=[str(topic.get("name")) for topic in _topic_nodes(raw) if topic.get("name")],
            makers=[
                str(maker.get("username") or maker.get("name"))
                for maker in _makers(raw)
                if maker.get("username") or maker.get("name")
            ],
            created_at=raw.get("createdAt"),
            featured_at=raw.get("featuredAt"),
            ranking=raw.get("dailyRank"),
            featured=raw.get("featuredAt") is not None,
        )
    except (TypeError, ValueError) as exc:
        raise TransformError(f"failed to normalize launch: {exc}") from exc


def normalize_product_detail(raw: dict) -> ProductDetail:
    if not isinstance(raw, dict):
        raise TransformError(f"expected dict, got {type(raw).__name__}")
    try:
        return ProductDetail(
            id=str(_require(raw, "id")),
            slug=str(_require(raw, "slug")),
            name=str(_require(raw, "name")),
            tagline=raw.get("tagline"),
            description=raw.get("description"),
            product_hunt_url=str(_require(raw, "url")),
            website_url=raw.get("website"),
            thumbnail_url=_thumbnail_url(raw),
            votes_count=_as_int(raw.get("votesCount")),
            comments_count=_as_int(raw.get("commentsCount")),
            reviews_count=raw.get("reviewsCount"),
            reviews_rating=raw.get("reviewsRating"),
            topics=[
                TopicRef(
                    id=str(_require(topic, "id")),
                    name=str(_require(topic, "name")),
                    slug=str(_require(topic, "slug")),
                    url=topic.get("url"),
                )
                for topic in _topic_nodes(raw)
            ],
            makers=[
                MakerRef(
                    id=str(_require(maker, "id")),
                    name=str(_require(maker, "name")),
                    username=str(_require(maker, "username")),
                    url=maker.get("url"),
                    twitter_username=maker.get("twitterUsername"),
                    headline=maker.get("headline"),
                    website_url=maker.get("websiteUrl"),
                )
                for maker in _makers(raw)
            ],
            media=[
                MediaRef(
                    type=str(item.get("type") or ""), url=str(_require(item, "url")), video_url=item.get("videoUrl")
                )
                for item in _media_items(raw)
            ],
            product_links=[
                ProductLinkRef(type=str(link.get("type") or ""), url=str(_require(link, "url")))
                for link in _product_links(raw)
            ],
            created_at=raw.get("createdAt"),
            featured_at=raw.get("featuredAt"),
            ranking=raw.get("dailyRank"),
            weekly_rank=raw.get("weeklyRank"),
            monthly_rank=raw.get("monthlyRank"),
            yearly_rank=raw.get("yearlyRank"),
            featured=raw.get("featuredAt") is not None,
        )
    except (TypeError, ValueError) as exc:
        raise TransformError(f"failed to normalize product detail: {exc}") from exc
