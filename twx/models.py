"""Typed models for twx normalized output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NormalizedMetrics(BaseModel):
    """Engagement metrics for a tweet."""

    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    view_count: int = 0
    bookmark_count: int = 0


class NormalizedMedia(BaseModel):
    """A single media attachment."""

    type: str  # photo, video, animated_gif
    url: str
    alt_text: str = ""


class NormalizedTweet(BaseModel):
    """A normalized tweet record."""

    id: str
    text: str
    url: str
    author_username: str
    author_name: str | None = None
    created_at: str  # ISO 8601
    metrics: NormalizedMetrics = Field(default_factory=NormalizedMetrics)
    media: list[NormalizedMedia] = Field(default_factory=list)
    is_retweet: bool = False
    is_reply: bool = False
    is_quote: bool = False


class NormalizedUser(BaseModel):
    """A normalized user record."""

    username: str
    name: str | None = None
    bio: str | None = None
    followers_count: int = 0
    following_count: int = 0
    tweet_count: int = 0


class SuccessEnvelope(BaseModel):
    """Stable success output envelope."""

    ok: bool = True
    data: dict = Field(default_factory=dict)
    paging: dict = Field(default_factory=lambda: {"next_cursor": None, "has_more": False})
    query: dict = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)
    raw: dict | None = None


class ErrorEnvelope(BaseModel):
    """Stable error output envelope."""

    ok: bool = False
    error: dict = Field(default_factory=dict)
