"""Typed models for phx normalized output and envelopes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NormalizedLaunch(BaseModel):
    type: Literal["launch"] = "launch"
    id: str
    slug: str
    name: str
    tagline: str | None
    description: str | None
    product_hunt_url: str
    website_url: str | None
    thumbnail_url: str | None
    votes_count: int
    comments_count: int
    topics: list[str] = Field(default_factory=list)
    makers: list[str] = Field(default_factory=list)
    created_at: str | None
    featured_at: str | None
    ranking: int | None
    featured: bool


class TopicRef(BaseModel):
    id: str
    name: str
    slug: str
    url: str | None = None


class MakerRef(BaseModel):
    id: str
    name: str
    username: str
    url: str | None = None
    twitter_username: str | None = None
    headline: str | None = None
    website_url: str | None = None


class MediaRef(BaseModel):
    type: str
    url: str
    video_url: str | None = None


class ProductLinkRef(BaseModel):
    type: str
    url: str


class ProductDetail(BaseModel):
    type: Literal["product"] = "product"
    id: str
    slug: str
    name: str
    tagline: str | None
    description: str | None
    product_hunt_url: str
    website_url: str | None
    thumbnail_url: str | None
    votes_count: int
    comments_count: int
    reviews_count: int | None = None
    reviews_rating: float | None = None
    topics: list[TopicRef] = Field(default_factory=list)
    makers: list[MakerRef] = Field(default_factory=list)
    media: list[MediaRef] = Field(default_factory=list)
    product_links: list[ProductLinkRef] = Field(default_factory=list)
    created_at: str | None
    featured_at: str | None
    ranking: int | None
    weekly_rank: int | None = None
    monthly_rank: int | None = None
    yearly_rank: int | None = None
    featured: bool


class SuccessEnvelope(BaseModel):
    ok: Literal[True] = True
    data: Any
    query: dict = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)
    raw: Any = None


class ErrorDetail(BaseModel):
    type: Literal["config_error", "upstream_error", "transform_error", "not_found", "invalid_input"]
    message: str
    details: dict = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    ok: Literal[False] = False
    error: ErrorDetail
