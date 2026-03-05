"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator


# ============================================================================
# User Schemas
# ============================================================================


class UserCreate(BaseModel):
    """Schema for creating a user."""

    name: Optional[str] = Field(None, max_length=255)
    email: EmailStr
    feishu_webhook_url: Optional[str] = Field(None, max_length=2048)
    feishu_webhook_secret: Optional[str] = Field(
        None,
        max_length=255,
        description="HMAC secret for Feishu webhook signature verification",
    )
    topics: List[str] = Field(default_factory=list, max_length=100)
    enable_feishu: bool = True
    enable_email: bool = True

    @validator("topics")
    def validate_topics(cls, v):
        """Validate topics field: UUID format, max count, no duplicates."""
        # Validate max count
        if len(v) > 100:
            raise ValueError("Maximum 100 topics per user exceeded")

        # Validate UUID format and detect duplicates
        seen = set()
        duplicates = set()
        invalid_uuids = []

        for item in v:
            # Check UUID format
            try:
                UUID(item)
            except ValueError:
                invalid_uuids.append(item)
                continue

            # Check for duplicates
            if item in seen:
                duplicates.add(item)
            seen.add(item)

        if invalid_uuids:
            raise ValueError(f"Invalid UUID format: {invalid_uuids}")

        if duplicates:
            raise ValueError(f"Duplicate topic IDs not allowed: {list(duplicates)}")

        return v


class UserResponse(BaseModel):
    """Schema for user response."""

    id: UUID
    name: Optional[str]
    email: str
    feishu_webhook_url: Optional[str]
    feishu_webhook_secret: Optional[str] = Field(
        None, description="HMAC secret for Feishu webhook (masked for security)"
    )
    topics: List[str] = []  # List of Topic UUID strings
    enable_feishu: bool = True
    enable_email: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class UserWithTopics(UserResponse):
    """Schema for user with topic details."""

    # Inherits all fields from UserResponse including topics

    class Config:
        from_attributes = True


# ============================================================================
# Topic Schemas
# ============================================================================


class TopicCreate(BaseModel):
    """Schema for creating a topic."""

    name: str = Field(..., max_length=255)
    query: str = Field(..., min_length=1)
    last_tweet_id: Optional[str] = Field(None, max_length=255)


class TopicUpdate(BaseModel):
    """Schema for updating a topic."""

    name: Optional[str] = Field(None, max_length=255)
    query: Optional[str] = Field(None, min_length=1)
    is_enabled: Optional[bool] = None


class TopicResponse(BaseModel):
    """Schema for topic response."""

    id: UUID
    name: str
    query: str
    is_enabled: bool
    last_collection_timestamp: Optional[datetime]
    last_tweet_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TopicWithStats(TopicResponse):
    """Schema for topic with statistics."""

    total_items: int = 0


# ============================================================================
# Item Schemas
# ============================================================================


class ItemResponse(BaseModel):
    """Schema for item response."""

    id: UUID
    topic_id: UUID
    source_id: str
    author: Optional[str]
    text: Optional[str]
    url: Optional[str]
    created_at: datetime
    collected_at: datetime
    media_urls: Optional[List[str]] = None
    metrics: Optional[dict] = None

    class Config:
        from_attributes = True


# ============================================================================
# User-Scoped Trigger Response Schemas
# ============================================================================


class UserTriggerResponse(BaseModel):
    """Schema for user-scoped manual trigger response with aggregated topic count."""

    status: str
    message: str
    task_id: Optional[str] = None
    user_id: UUID
    topic_count: int
    time_window: Optional[str] = None

    class Config:
        from_attributes = True


class UserDigestResponse(BaseModel):
    """Schema for aggregated digest response metadata for a user."""

    id: UUID
    user_id: UUID
    topic_ids: List[UUID]
    time_window_start: datetime
    time_window_end: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Health Check Schemas
# ============================================================================


class ComponentHealth(BaseModel):
    """Schema for component health status."""

    status: str
    message: Optional[str] = None
    latency_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    app_name: str
    version: str
    components: dict[str, ComponentHealth]


# ============================================================================
# List Response Wrapper
# ============================================================================


class PaginatedResponse(BaseModel):
    """Schema for paginated list response."""

    items: List
    total: int
    limit: int
    offset: int
    has_more: bool

    @classmethod
    def create(cls, items: List, total: int, limit: int, offset: int):
        """Create paginated response."""
        has_more = offset + limit < total
        return cls(items=items, total=total, limit=limit, offset=offset, has_more=has_more)


# ============================================================================
# Resolve Forward References
# ============================================================================

# Rebuild models that use forward references
UserWithTopics.model_rebuild()
