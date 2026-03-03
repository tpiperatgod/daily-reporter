"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================================
# User Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Schema for creating a user."""
    name: Optional[str] = Field(None, max_length=255)
    email: EmailStr
    feishu_webhook_url: Optional[str] = Field(None, max_length=2048)
    feishu_webhook_secret: Optional[str] = Field(None, max_length=255)
    topics: List[str] = Field(default_factory=list, max_length=100)
    enable_feishu: bool = True
    enable_email: bool = True

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: List[str]) -> List[str]:
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

class UserUpdate(BaseModel):
    """Schema for updating a user."""
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    feishu_webhook_url: Optional[str] = Field(None, max_length=2048)
    feishu_webhook_secret: Optional[str] = Field(None, max_length=255)


class UserResponse(BaseModel):
    """Schema for user response."""
    id: UUID
    name: Optional[str]
    email: str
    feishu_webhook_url: Optional[str]
    feishu_webhook_secret: Optional[str]
    topics: List[str] = []  # List of Topic UUID strings
    enable_feishu: bool = True
    enable_email: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}

    model_config = {"from_attributes": True}


class UserWithTopics(UserResponse):
    """Schema for user with topic details."""
    # Inherits all fields from UserResponse including topics

    model_config = {"from_attributes": True}


# ============================================================================
# Topic Schemas
# ============================================================================

class TopicCreate(BaseModel):
    """Schema for creating a topic."""
    name: str = Field(..., max_length=255)
    query: str = Field(..., min_length=1)
    cron_expression: str = Field(..., max_length=100)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate cron expression format."""
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError(
                "Invalid cron expression. Expected format: 'minute hour day month weekday'"
            )
        return v


class TopicUpdate(BaseModel):
    """Schema for updating a topic."""
    name: Optional[str] = Field(None, max_length=255)
    query: Optional[str] = Field(None, min_length=1)
    cron_expression: Optional[str] = Field(None, max_length=100)
    is_enabled: Optional[bool] = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """Validate cron expression format if provided."""
        if v is not None:
            parts = v.strip().split()
            if len(parts) != 5:
                raise ValueError(
                    "Invalid cron expression. Expected format: 'minute hour day month weekday'"
                )
        return v


class TopicResponse(BaseModel):
    """Schema for topic response."""
    id: UUID
    name: str
    query: str
    cron_expression: str
    is_enabled: bool
    last_collection_timestamp: Optional[datetime]
    last_tweet_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TopicWithStats(TopicResponse):
    """Schema for topic with statistics."""
    total_items: int = 0
    total_digests: int = 0

# ============================================================================
# Digest Schemas
# ============================================================================

class DigestStatsResponse(BaseModel):
    """Schema for digest statistics."""
    total_posts_analyzed: int
    unique_authors: int
    total_engagement: int
    avg_engagement_per_post: float


class DigestHighlight(BaseModel):
    """Schema for digest highlight."""
    title: str
    summary: str
    representative_urls: List[str]
    score: int


class DigestSummary(BaseModel):
    """Schema for digest summary (from LLM)."""
    headline: str
    highlights: List[DigestHighlight]
    themes: List[str]
    sentiment: str
    stats: DigestStatsResponse


class DigestResponse(BaseModel):
    """Schema for digest response."""
    id: UUID
    topic_id: UUID
    time_window_start: datetime
    time_window_end: datetime
    summary_json: dict
    rendered_content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DigestWithDetails(DigestResponse):
    """Schema for digest with topic and delivery details."""
    topic: TopicResponse
    deliveries: List["DeliveryResponse"] = []


# ============================================================================
# Delivery Schemas
# ============================================================================

class DeliveryResponse(BaseModel):
    """Schema for delivery response."""
    id: UUID
    digest_id: Optional[UUID] = None
    user_digest_id: Optional[UUID] = None
    user_id: UUID
    channel: str
    status: str
    retry_count: int
    error_msg: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

# ============================================================================
# Send Digest Schemas
# ============================================================================

class SendDigestDelivery(BaseModel):
    """Schema for delivery info in send digest response."""
    id: UUID
    channel: str
    status: str
    sent_at: Optional[datetime]
    error_msg: Optional[str]

    model_config = {"from_attributes": True}


class SendDigestResponse(BaseModel):
    digest_id: UUID
    user_id: UUID
    deliveries: List[SendDigestDelivery]
    total_sent: int
    successful: int
    failed: int

    model_config = {"from_attributes": True}

# ============================================================================
# Trigger Response Schemas
# ============================================================================

# Trigger Response Schemas
# ============================================================================

class TriggerResponse(BaseModel):
    """Schema for manual trigger response."""
    status: str
    message: str
    task_id: Optional[str] = None
    topic_id: Optional[str] = None


class UserTriggerResponse(BaseModel):
    """Response from user trigger endpoint."""
    status: str
    message: str
    task_id: Optional[str] = None
    user_id: UUID
    topic_count: int

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
