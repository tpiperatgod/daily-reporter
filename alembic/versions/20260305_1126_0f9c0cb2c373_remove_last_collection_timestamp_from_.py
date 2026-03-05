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
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_topics_enabled_last_run", table_name="topics")
    op.drop_column("topics", "last_collection_timestamp")


def downgrade() -> None:
    op.add_column("topics", sa.Column("last_collection_timestamp", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_topics_enabled_last_run", "topics", ["is_enabled", "last_collection_timestamp"], unique=False)
