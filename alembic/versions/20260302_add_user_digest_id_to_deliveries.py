"""Add user_digest_id to deliveries for user-scoped digest support

Revision ID: 20260302_user_digest_delivery
Revises: 003
Create Date: 2026-03-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260302_user_digest_delivery"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_digest_id column (nullable, FK to user_digests.id)
    op.add_column(
        "deliveries",
        sa.Column(
            "user_digest_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_digests.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )

    # Make digest_id nullable (was NOT NULL)
    op.alter_column(
        "deliveries",
        "digest_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # Add CHECK constraint: exactly one of digest_id or user_digest_id must be non-null
    op.create_check_constraint(
        "chk_deliveries_one_digest_target",
        "deliveries",
        "(digest_id IS NOT NULL AND user_digest_id IS NULL) OR (digest_id IS NULL AND user_digest_id IS NOT NULL)",
    )

    # Add composite index for efficient lookups by user_digest_id and status
    op.create_index(
        "ix_deliveries_user_digest_status",
        "deliveries",
        ["user_digest_id", "status"],
    )


def downgrade() -> None:
    # Drop index on user_digest_id and status
    op.drop_index("ix_deliveries_user_digest_status", table_name="deliveries")

    # Drop CHECK constraint
    op.drop_constraint("chk_deliveries_one_digest_target", "deliveries", type_="check")

    # Revert digest_id to NOT NULL
    # Note: This will fail if there are deliveries with digest_id=NULL
    op.alter_column(
        "deliveries",
        "digest_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # Drop user_digest_id column
    op.drop_column("deliveries", "user_digest_id")
