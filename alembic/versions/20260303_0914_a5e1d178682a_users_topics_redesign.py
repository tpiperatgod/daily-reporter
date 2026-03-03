"""users_topics_redesign

Revision ID: a5e1d178682a
Revises: 20260302_user_digest_delivery
Create Date: 2026-03-03 09:14:20.107807

"""

from typing import Sequence, Union

from alembic import op


revision: str = "a5e1d178682a"
down_revision: Union[str, None] = "20260302_user_digest_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Structural migration for users.topics redesign.

    Adds:
    - users.topics: JSONB NOT NULL DEFAULT '[]'::jsonb
    - users.enable_feishu: BOOLEAN NOT NULL DEFAULT true
    - users.enable_email: BOOLEAN NOT NULL DEFAULT true
    - GIN index ix_users_topics for efficient JSONB queries

    Drops:
    - subscriptions table and its indexes
    """

    # Add/fix topics column (JSONB)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name='users' AND column_name='topics') THEN
                ALTER TABLE users
                    ALTER COLUMN topics SET NOT NULL,
                    ALTER COLUMN topics SET DEFAULT '[]'::jsonb;
            ELSE
                ALTER TABLE users ADD COLUMN topics JSONB NOT NULL DEFAULT '[]'::jsonb;
            END IF;
        END $$;
    """)

    # Add/fix enable_feishu column (BOOLEAN)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name='users' AND column_name='enable_feishu') THEN
                ALTER TABLE users
                    ALTER COLUMN enable_feishu SET NOT NULL,
                    ALTER COLUMN enable_feishu SET DEFAULT true;
            ELSE
                ALTER TABLE users ADD COLUMN enable_feishu BOOLEAN NOT NULL DEFAULT true;
            END IF;
        END $$;
    """)

    # Add/fix enable_email column (BOOLEAN)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name='users' AND column_name='enable_email') THEN
                ALTER TABLE users
                    ALTER COLUMN enable_email SET NOT NULL,
                    ALTER COLUMN enable_email SET DEFAULT true;
            ELSE
                ALTER TABLE users ADD COLUMN enable_email BOOLEAN NOT NULL DEFAULT true;
            END IF;
        END $$;
    """)

    # Create GIN index for efficient JSONB queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_topics
        ON users USING GIN (topics jsonb_path_ops);
    """)

    # ========================================================================
    # DATA MIGRATION: Populate users.topics from subscriptions
    # ========================================================================
    # Migrate subscription data to user-level fields before dropping table:
    # - topics: Array of unique topic UUIDs (DISTINCT to handle duplicates)
    # - enable_feishu: OR aggregation of subscription flags (default true)
    # - enable_email: OR aggregation of subscription flags (default true)
    
    op.execute("""
        UPDATE users u
        SET 
            topics = COALESCE(
                (SELECT jsonb_agg(DISTINCT s.topic_id)
                 FROM subscriptions s
                 WHERE s.user_id = u.id),
                '[]'::jsonb
            ),
            enable_feishu = COALESCE(
                (SELECT bool_or(s.enable_feishu)
                 FROM subscriptions s
                 WHERE s.user_id = u.id),
                true
            ),
            enable_email = COALESCE(
                (SELECT bool_or(s.enable_email)
                 FROM subscriptions s
                 WHERE s.user_id = u.id),
                true
            );
    """)

    # Drop subscriptions table
    op.execute("""
        DROP INDEX IF EXISTS ix_subscriptions_topic_id;
    """)

    op.execute("""
        DROP TABLE IF EXISTS subscriptions CASCADE;
    """)


def downgrade() -> None:
    """
    Rollback is NOT SUPPORTED per contract.

    Once subscriptions table is dropped, there is no automatic rollback.
    Manual backup required before migration.
    """

    # Recreate subscriptions table
    op.execute("""
        CREATE TABLE subscriptions (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            topic_id UUID NOT NULL,
            enable_feishu BOOLEAN NOT NULL DEFAULT true,
            enable_email BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT pk_subscriptions PRIMARY KEY (id),
            CONSTRAINT fk_subscriptions_user_id FOREIGN KEY (user_id)
                REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_subscriptions_topic_id FOREIGN KEY (topic_id)
                REFERENCES topics(id) ON DELETE CASCADE
        );
    """)

    # Recreate index
    op.execute("""
        CREATE INDEX ix_subscriptions_topic_id ON subscriptions(topic_id);
    """)

    # Drop GIN index
    op.execute("""
        DROP INDEX IF EXISTS ix_users_topics;
    """)

    # Drop new columns from users
    op.execute("""
        ALTER TABLE users DROP COLUMN IF EXISTS enable_email;
    """)
    op.execute("""
        ALTER TABLE users DROP COLUMN IF EXISTS enable_feishu;
    """)
    op.execute("""
        ALTER TABLE users DROP COLUMN IF EXISTS topics;
    """)
