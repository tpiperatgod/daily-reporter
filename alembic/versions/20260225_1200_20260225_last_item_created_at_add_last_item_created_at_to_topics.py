"""Add last_item_created_at to topics and ix_items_topic_created index

Revision ID: 20260225_last_item_created_at
Revises: f771473dec7c
Create Date: 2026-02-25

Notes on zero-downtime safety:
- ADD COLUMN (nullable, no default): metadata-only in PostgreSQL 11+, instant.
- CREATE INDEX CONCURRENTLY: runs without holding a write lock on items.
  Requires autocommit (cannot run inside a transaction block).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260225_last_item_created_at'
down_revision: Union[str, None] = 'f771473dec7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Instant in PostgreSQL 11+: no table rewrite, only a brief ACCESS EXCLUSIVE
    # lock to update pg_catalog. Safe to run while the app is live.
    op.add_column('topics', sa.Column('last_item_created_at', sa.DateTime(timezone=True), nullable=True))

    # CREATE INDEX CONCURRENTLY does not hold a write lock on items while building.
    # It must run outside a transaction block, so we use autocommit_block().
    with op.get_context().autocommit_block():
        op.execute(sa.text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_items_topic_created ON items (topic_id, created_at)"
        ))


def downgrade() -> None:
    # DROP INDEX CONCURRENTLY also requires autocommit.
    with op.get_context().autocommit_block():
        op.execute(sa.text(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_items_topic_created"
        ))

    op.drop_column('topics', 'last_item_created_at')
