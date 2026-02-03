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
    created_at: datetime

    model_config = {"from_attributes": True}


class UserWithSubscriptions(UserResponse):
    """Schema for user with subscription details."""
    subscriptions: List["SubscriptionWithTopic"] = []

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
    total_subscriptions: int = 0


# ============================================================================
# Subscription Schemas
# ============================================================================

class SubscriptionCreate(BaseModel):
    """Schema for creating a subscription."""
    user_id: UUID
    topic_id: UUID
    enable_feishu: bool = True
    enable_email: bool = True


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""
    enable_feishu: Optional[bool] = None
    enable_email: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""
    id: UUID
    user_id: UUID
    topic_id: UUID
    enable_feishu: bool
    enable_email: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionWithTopic(SubscriptionResponse):
    """Schema for subscription with topic details."""
    topic: Optional[TopicResponse] = None

    model_config = {"from_attributes": True}


class SubscriptionWithDetails(SubscriptionResponse):
    """Schema for subscription with user and topic details."""
    user: UserResponse
    topic: TopicResponse

    model_config = {"from_attributes": True}


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
    digest_id: UUID
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
    """Schema for send digest response."""
    digest_id: UUID
    subscription_id: UUID
    deliveries: List[SendDigestDelivery]
    total_sent: int
    successful: int
    failed: int


# ============================================================================
# Trigger Response Schemas
# ============================================================================

class TriggerResponse(BaseModel):
    """Schema for manual trigger response."""
    status: str
    message: str
    task_id: Optional[str] = None
    topic_id: Optional[str] = None


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
