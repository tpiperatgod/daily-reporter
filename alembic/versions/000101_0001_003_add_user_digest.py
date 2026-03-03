"""Add user_digests table for user-scoped aggregated digests

Revision ID: 003
Revises: 20260225_last_item_created_at
Create Date: 2026-03-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "20260225_last_item_created_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_digests table for user-scoped aggregated digests
    op.create_table(
        "user_digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("topic_ids", postgresql.JSONB(), nullable=False),
        sa.Column("time_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("time_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_json", postgresql.JSONB(), nullable=False),
        sa.Column("rendered_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    # Composite index for efficient user digest queries
    op.create_index("ix_user_digests_user_created", "user_digests", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_user_digests_user_created", table_name="user_digests")
    op.drop_table("user_digests")
