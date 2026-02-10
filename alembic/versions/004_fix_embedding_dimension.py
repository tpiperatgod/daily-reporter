"""Fix embedding dimension to match bge-m3 model (1024)

Revision ID: 004
Revises: 003
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old HNSW index
    op.execute('DROP INDEX IF EXISTS ix_memory_facts_embedding_hnsw')

    # Change vector dimension from 1536 to 1024 (for bge-m3 model)
    op.execute('ALTER TABLE memory_facts ALTER COLUMN embedding TYPE vector(1024)')

    # Recreate HNSW index with same parameters
    op.execute("""
        CREATE INDEX ix_memory_facts_embedding_hnsw
        ON memory_facts
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    # Drop HNSW index
    op.execute('DROP INDEX IF EXISTS ix_memory_facts_embedding_hnsw')

    # Revert vector dimension back to 1536
    op.execute('ALTER TABLE memory_facts ALTER COLUMN embedding TYPE vector(1536)')

    # Recreate HNSW index
    op.execute("""
        CREATE INDEX ix_memory_facts_embedding_hnsw
        ON memory_facts
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
