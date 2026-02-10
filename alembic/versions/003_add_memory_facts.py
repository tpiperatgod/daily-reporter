"""Add memory_facts table with pgvector support

Revision ID: 003
Revises: 002
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = 'f771473dec7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create memory_facts table
    op.create_table(
        'memory_facts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('topic_id', UUID(as_uuid=True), sa.ForeignKey('topics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=False),  # Will be vector(1536) type
        sa.Column('source_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Change embedding column to vector type
    op.execute('ALTER TABLE memory_facts ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)')
    
    # Create standard indexes
    op.create_index('ix_memory_facts_topic_created', 'memory_facts', ['topic_id', 'created_at'])
    
    # Create HNSW index for vector similarity search
    op.execute("""
        CREATE INDEX ix_memory_facts_embedding_hnsw 
        ON memory_facts 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_memory_facts_embedding_hnsw', table_name='memory_facts')
    op.drop_index('ix_memory_facts_topic_created', table_name='memory_facts')
    
    # Drop table
    op.drop_table('memory_facts')
    
    # Note: We don't drop the vector extension as other tables might use it
