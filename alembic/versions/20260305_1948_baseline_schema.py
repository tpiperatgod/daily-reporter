"""baseline schema

Create all required database tables with proper relationships and indexes.

Revision ID: baseline_schema
Revises:
Create Date: 2026-03-05 19:48:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# revision identifiers, used by Alembic.
revision: str = "baseline_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if tables already exist (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Skip if schema already exists
    if "users" in existing_tables:
        return

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("feishu_webhook_url", sa.Text, nullable=True),
        sa.Column("feishu_webhook_secret", sa.String(255), nullable=True),
        sa.Column("topics", JSONB, nullable=False, server_default="[]"),
        sa.Column("enable_feishu", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("enable_email", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Create topics table
    op.create_table(
        "topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_tweet_id", sa.String(255), nullable=True),
        sa.Column("last_item_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_topics_last_tweet_id", "topics", ["last_tweet_id"])

    # Create items table
    op.create_table(
        "items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("topic_id", UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("text", sa.Text, nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("media_urls", JSONB, nullable=True),
        sa.Column("metrics", JSONB, nullable=True),
        sa.Column("embedding_hash", sa.String(64), nullable=True),
    )
    op.create_index("ix_items_source_id", "items", ["source_id"], unique=True)
    op.create_index("ix_items_topic_collected", "items", ["topic_id", "collected_at"])
    op.create_index("ix_items_topic_created", "items", ["topic_id", "created_at"])
    op.create_index("ix_items_embedding_hash", "items", ["embedding_hash"])

    # Create user_digests table
    op.create_table(
        "user_digests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("time_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("time_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("rendered_content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_user_digests_user_created", "user_digests", ["user_id", "created_at"])

    # Create deliveries table
    op.create_table(
        "deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_digest_id", UUID(as_uuid=True), sa.ForeignKey("user_digests.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_msg", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_deliveries_user_digest_status", "deliveries", ["user_digest_id", "status"])


def downgrade() -> None:
    # Drop in reverse order of creation (respecting foreign keys)
    op.drop_index("ix_deliveries_user_digest_status", table_name="deliveries")
    op.drop_table("deliveries")

    op.drop_index("ix_user_digests_user_created", table_name="user_digests")
    op.drop_table("user_digests")

    op.drop_index("ix_items_embedding_hash", table_name="items")
    op.drop_index("ix_items_topic_created", table_name="items")
    op.drop_index("ix_items_topic_collected", table_name="items")
    op.drop_index("ix_items_source_id", table_name="items")
    op.drop_table("items")

    op.drop_index("ix_topics_last_tweet_id", table_name="topics")
    op.drop_table("topics")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
