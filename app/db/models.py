from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class User(Base):
    """User model for storing user information."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    feishu_webhook_url = Column(Text, nullable=True)
    feishu_webhook_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    deliveries = relationship("Delivery", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"


class Topic(Base):
    """Topic model for storing Twitter/X search topics."""

    __tablename__ = "topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    query = Column(Text, nullable=False)
    cron_expression = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    last_collection_timestamp = Column(DateTime(timezone=True), nullable=True)
    last_tweet_id = Column(String(255), nullable=True, index=True)
    last_item_created_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subscriptions = relationship("Subscription", back_populates="topic", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="topic", cascade="all, delete-orphan")
    digests = relationship("Digest", back_populates="topic", cascade="all, delete-orphan")

    # Index for scheduling queries
    __table_args__ = (Index("ix_topics_enabled_last_run", "is_enabled", "last_collection_timestamp"),)

    def __repr__(self):
        return f"<Topic {self.name}>"


class Subscription(Base):
    """Subscription model linking users to topics."""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    enable_feishu = Column(Boolean, default=True, nullable=False)
    enable_email = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    topic = relationship("Topic", back_populates="subscriptions")

    # Unique constraint and index
    __table_args__ = (Index("ix_subscriptions_topic_id", "topic_id"),)

    def __repr__(self):
        return f"<Subscription user={self.user_id} topic={self.topic_id}>"


class Item(Base):
    """Item model for storing collected tweets/posts."""

    __tablename__ = "items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(String(255), nullable=False, unique=True, index=True)
    author = Column(String(255), nullable=True)
    text = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)  # Tweet creation time
    collected_at = Column(DateTime(timezone=True), server_default=func.now())  # When we fetched it
    media_urls = Column(JSONB, nullable=True)
    metrics = Column(JSONB, nullable=True)  # likes, retweets, replies, views
    embedding_hash = Column(String(64), nullable=True, index=True)

    # Relationships
    topic = relationship("Topic", back_populates="items")

    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_items_topic_collected", "topic_id", "collected_at"),
        Index("ix_items_topic_created", "topic_id", "created_at"),
        Index("ix_items_embedding_hash", "embedding_hash"),
    )

    def __repr__(self):
        return f"<Item {self.source_id}>"


class Digest(Base):
    """Digest model for storing generated summaries."""

    __tablename__ = "digests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    time_window_start = Column(DateTime(timezone=True), nullable=False)
    time_window_end = Column(DateTime(timezone=True), nullable=False)
    summary_json = Column(JSONB, nullable=False)  # Structured DigestResult
    rendered_content = Column(Text, nullable=False)  # Markdown
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    topic = relationship("Topic", back_populates="digests")
    deliveries = relationship("Delivery", back_populates="digest", cascade="all, delete-orphan")

    # Index for efficient queries
    __table_args__ = (Index("ix_digests_topic_created", "topic_id", "created_at"),)

    def __repr__(self):
        return f"<Digest {self.id}>"


class Delivery(Base):
    """Delivery model for tracking notification delivery status."""

    __tablename__ = "deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    digest_id = Column(UUID(as_uuid=True), ForeignKey("digests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(50), nullable=False)  # 'feishu' or 'email'
    status = Column(String(50), nullable=False, default="pending")  # 'pending', 'success', 'failed'
    retry_count = Column(Integer, default=0, nullable=False)
    error_msg = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    digest = relationship("Digest", back_populates="deliveries")
    user = relationship("User", back_populates="deliveries")

    # Index for efficient queries
    __table_args__ = (Index("ix_deliveries_digest_status", "digest_id", "status"),)

    def __repr__(self):
        return f"<Delivery {self.channel} - {self.status}>"
