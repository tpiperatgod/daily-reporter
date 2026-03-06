"""remove last_collection_timestamp from topics

Revision ID: 0f9c0cb2c373
Revises:
Create Date: 2026-03-05 11:26:13.910897

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0f9c0cb2c373"
down_revision: Union[str, None] = "baseline_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table exists first (for fresh databases)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Get list of existing tables
    existing_tables = inspector.get_table_names()

    if "topics" not in existing_tables:
        # Fresh database - nothing to drop
        return

    # Check if index exists before dropping
    try:
        indexes = inspector.get_indexes("topics")
        index_names = [idx["name"] for idx in indexes]

        if "ix_topics_enabled_last_run" in index_names:
            op.drop_index("ix_topics_enabled_last_run", table_name="topics")
    except sa.exc.NoSuchTableError:
        pass

    # Check if column exists before dropping
    try:
        columns = [col["name"] for col in inspector.get_columns("topics")]
        if "last_collection_timestamp" in columns:
            op.drop_column("topics", "last_collection_timestamp")
    except sa.exc.NoSuchTableError:
        pass


def downgrade() -> None:
    op.add_column("topics", sa.Column("last_collection_timestamp", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_topics_enabled_last_run", "topics", ["is_enabled", "last_collection_timestamp"], unique=False)
