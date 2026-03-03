"""Add last_tweet_id to topics

Revision ID: 002
Revises: 001
Create Date: 2025-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add last_tweet_id column to topics table
    op.add_column('topics', sa.Column('last_tweet_id', sa.String(255), nullable=True))
    op.create_index('ix_topics_last_tweet_id', 'topics', ['last_tweet_id'])


def downgrade() -> None:
    # Remove last_tweet_id column and index
    op.drop_index('ix_topics_last_tweet_id', table_name='topics')
    op.drop_column('topics', 'last_tweet_id')
