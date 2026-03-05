"""Tests for users.topics data migration logic.

These tests verify the data migration portion of Alembic migration
20260303_0914_a5e1d178682a (users_topics_redesign).

The migration populates:
- users.topics: Array of unique topic UUIDs from subscriptions
- users.enable_feishu: OR aggregation of subscription flags
- users.enable_email: OR aggregation of subscription flags
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Topic
from app.db.session import get_async_session_local


@pytest_asyncio.fixture
async def async_session():
    AsyncSessionLocal = get_async_session_local()
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id UUID NOT NULL,
                user_id UUID NOT NULL,
                topic_id UUID NOT NULL,
                enable_feishu BOOLEAN NOT NULL DEFAULT true,
                enable_email BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
        """)
        )
        await session.commit()
        yield session
        try:
            await session.rollback()
            await session.execute(text("DROP TABLE IF EXISTS subscriptions"))
            await session.commit()
        except Exception:
            pass


@pytest_asyncio.fixture
async def test_topics(async_session):
    """Create test topics for migration testing."""
    topics = []
    for i in range(5):
        topic = Topic(
            id=uuid4(),
            name=f"Migration Test Topic {i} {uuid4()}",
            query=f"@migration_test_{i}_{uuid4()}",
            # cron_expression removed - topic-scoped scheduling decommissioned
            is_enabled=True,
            last_tweet_id=None,
        )
        async_session.add(topic)
        topics.append(topic)

    await async_session.commit()
    for topic in topics:
        await async_session.refresh(topic)

    return topics


class TestMigrationDataIntegrity:
    """Test data migration correctness."""

    async def _create_user_with_subscriptions(
        self,
        session: AsyncSession,
        email: str,
        topic_ids: list,
        feishu_flags: list,
        email_flags: list,
    ):
        """Helper to create user with subscriptions via raw SQL."""
        user_id = uuid4()
        unique_email = f"{email}.{uuid4()}@test.local"

        await session.execute(
            text("""
                INSERT INTO users (id, name, email, schedule, topics, enable_feishu, enable_email)
                VALUES (:id, :name, :email, '0 9 * * *', '[]'::jsonb, true, true)
            """),
            {"id": user_id, "name": f"Test User {email}", "email": unique_email},
        )

        for i, (topic_id, feishu, email_flag) in enumerate(zip(topic_ids, feishu_flags, email_flags)):
            await session.execute(
                text("""
                    INSERT INTO subscriptions (id, user_id, topic_id, enable_feishu, enable_email)
                    VALUES (:id, :user_id, :topic_id, :feishu, :email)
                """),
                {
                    "id": uuid4(),
                    "user_id": user_id,
                    "topic_id": topic_id,
                    "feishu": feishu,
                    "email": email_flag,
                },
            )

        await session.commit()
        return user_id

    async def _run_migration_update(self, session: AsyncSession):
        """Run the data migration UPDATE statement."""
        await session.execute(
            text("""
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
                    )
            """)
        )
        await session.commit()

    @pytest.mark.asyncio
    async def test_user_with_multiple_subscriptions(self, async_session, test_topics):
        """Test user with multiple subscriptions gets correct topics array."""
        topic_ids = [str(t.id) for t in test_topics[:3]]

        user_id = await self._create_user_with_subscriptions(
            session=async_session,
            email="multi_sub",
            topic_ids=topic_ids,
            feishu_flags=[True, True, True],
            email_flags=[True, True, True],
        )

        await self._run_migration_update(async_session)

        result = await async_session.execute(
            text("SELECT topics, enable_feishu, enable_email FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row is not None
        topics = row[0]
        enable_feishu = row[1]
        enable_email = row[2]

        assert len(topics) == 3
        for tid in topic_ids:
            assert tid in topics

        assert enable_feishu is True
        assert enable_email is True

    @pytest.mark.asyncio
    async def test_user_with_zero_subscriptions(self, async_session):
        """Test user with no subscriptions gets empty array and default flags."""
        user_id = uuid4()
        unique_email = f"no_subs.{uuid4()}@test.local"

        await async_session.execute(
            text("""
                INSERT INTO users (id, name, email, schedule, topics, enable_feishu, enable_email)
                VALUES (:id, :name, :email, '0 9 * * *', '[]'::jsonb, true, true)
            """),
            {
                "id": user_id,
                "name": "No Subscriptions User",
                "email": unique_email,
            },
        )
        await async_session.commit()

        await self._run_migration_update(async_session)

        result = await async_session.execute(
            text("SELECT topics, enable_feishu, enable_email FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row is not None
        topics = row[0]
        enable_feishu = row[1]
        enable_email = row[2]

        assert topics == []
        assert enable_feishu is True
        assert enable_email is True

    @pytest.mark.asyncio
    async def test_duplicate_topic_ids_handled(self, async_session, test_topics):
        """Test that duplicate topic IDs in subscriptions are deduplicated."""
        topic_id = str(test_topics[0].id)
        unique_email = f"duplicate.{uuid4()}@test.local"

        user_id = uuid4()
        await async_session.execute(
            text("""
                INSERT INTO users (id, name, email, schedule, topics, enable_feishu, enable_email)
                VALUES (:id, :name, :email, '0 9 * * *', '[]'::jsonb, true, true)
            """),
            {
                "id": user_id,
                "name": "Duplicate Topic User",
                "email": unique_email,
            },
        )

        for i in range(3):
            await async_session.execute(
                text("""
                    INSERT INTO subscriptions (id, user_id, topic_id, enable_feishu, enable_email)
                    VALUES (:id, :user_id, :topic_id, true, true)
                """),
                {
                    "id": uuid4(),
                    "user_id": user_id,
                    "topic_id": topic_id,
                },
            )
        await async_session.commit()

        await self._run_migration_update(async_session)

        result = await async_session.execute(
            text("SELECT topics FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row is not None
        topics = row[0]

        assert len(topics) == 1
        assert topics[0] == topic_id

    @pytest.mark.asyncio
    async def test_flag_aggregation_feishu_or(self, async_session, test_topics):
        """Test enable_feishu uses OR aggregation (any True = True)."""
        topic_ids = [str(t.id) for t in test_topics[:3]]

        user_id = await self._create_user_with_subscriptions(
            session=async_session,
            email="feishu_or",
            topic_ids=topic_ids,
            feishu_flags=[False, False, True],
            email_flags=[True, True, True],
        )

        await self._run_migration_update(async_session)

        result = await async_session.execute(
            text("SELECT enable_feishu FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row is not None
        assert row[0] is True

    @pytest.mark.asyncio
    async def test_flag_aggregation_email_or(self, async_session, test_topics):
        """Test enable_email uses OR aggregation (any True = True)."""
        topic_ids = [str(t.id) for t in test_topics[:3]]

        user_id = await self._create_user_with_subscriptions(
            session=async_session,
            email="email_or",
            topic_ids=topic_ids,
            feishu_flags=[True, True, True],
            email_flags=[True, False, False],
        )

        await self._run_migration_update(async_session)

        result = await async_session.execute(
            text("SELECT enable_email FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row is not None
        assert row[0] is True

    @pytest.mark.asyncio
    async def test_flag_aggregation_all_false(self, async_session, test_topics):
        """Test flag aggregation when all subscriptions have False flags."""
        topic_ids = [str(t.id) for t in test_topics[:2]]

        user_id = await self._create_user_with_subscriptions(
            session=async_session,
            email="all_false",
            topic_ids=topic_ids,
            feishu_flags=[False, False],
            email_flags=[False, False],
        )

        await self._run_migration_update(async_session)

        result = await async_session.execute(
            text("SELECT enable_feishu, enable_email FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row is not None
        assert row[0] is False
        assert row[1] is False

    @pytest.mark.asyncio
    async def test_mixed_flag_scenarios(self, async_session, test_topics):
        """Test various combinations of channel flags across subscriptions."""
        topic_ids = [str(t.id) for t in test_topics[:4]]

        user_id = await self._create_user_with_subscriptions(
            session=async_session,
            email="mixed_flags",
            topic_ids=topic_ids,
            feishu_flags=[True, False, True, False],
            email_flags=[False, False, False, True],
        )

        await self._run_migration_update(async_session)

        result = await async_session.execute(
            text("SELECT topics, enable_feishu, enable_email FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row is not None
        topics = row[0]
        enable_feishu = row[1]
        enable_email = row[2]

        assert len(topics) == 4
        for tid in topic_ids:
            assert tid in topics

        assert enable_feishu is True
        assert enable_email is True


class TestMigrationEdgeCases:
    """Test edge cases in migration logic."""

    async def _create_user_with_subscriptions(
        self,
        session: AsyncSession,
        email: str,
        topic_ids: list,
        feishu_flags: list,
        email_flags: list,
    ):
        """Helper to create user with subscriptions via raw SQL."""
        user_id = uuid4()
        unique_email = f"{email}.{uuid4()}@test.local"

        await session.execute(
            text("""
                INSERT INTO users (id, name, email, schedule, topics, enable_feishu, enable_email)
                VALUES (:id, :name, :email, '0 9 * * *', '[]'::jsonb, true, true)
            """),
            {"id": user_id, "name": f"Test User {email}", "email": unique_email},
        )

        for i, (topic_id, feishu, email_flag) in enumerate(zip(topic_ids, feishu_flags, email_flags)):
            await session.execute(
                text("""
                    INSERT INTO subscriptions (id, user_id, topic_id, enable_feishu, enable_email)
                    VALUES (:id, :user_id, :topic_id, :feishu, :email)
                """),
                {
                    "id": uuid4(),
                    "user_id": user_id,
                    "topic_id": topic_id,
                    "feishu": feishu,
                    "email": email_flag,
                },
            )

        await session.commit()
        return user_id

    async def _run_migration_update(self, session: AsyncSession):
        """Run the data migration UPDATE statement."""
        await session.execute(
            text("""
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
                    )
            """)
        )
        await session.commit()

    @pytest.mark.asyncio
    async def test_single_subscription(self, async_session, test_topics):
        """Test user with exactly one subscription."""
        topic_id = str(test_topics[0].id)

        user_id = await self._create_user_with_subscriptions(
            session=async_session,
            email="single_sub",
            topic_ids=[topic_id],
            feishu_flags=[False],
            email_flags=[True],
        )

        await self._run_migration_update(async_session)

        result = await async_session.execute(
            text("SELECT topics, enable_feishu, enable_email FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row is not None
        assert row[0] == [topic_id]
        assert row[1] is False
        assert row[2] is True

    @pytest.mark.asyncio
    async def test_many_subscriptions(self, async_session, test_topics):
        """Test user with many subscriptions (boundary case)."""
        topic_ids = [str(t.id) for t in test_topics] * 3
        feishu_flags = [True] * 15
        email_flags = [True] * 15

        user_id = await self._create_user_with_subscriptions(
            session=async_session,
            email="many_subs",
            topic_ids=topic_ids,
            feishu_flags=feishu_flags,
            email_flags=email_flags,
        )

        await self._run_migration_update(async_session)

        result = await async_session.execute(
            text("SELECT topics, enable_feishu, enable_email FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row is not None
        topics = row[0]

        assert len(topics) == 5
        unique_topic_ids = list(set(topic_ids))
        for tid in unique_topic_ids:
            assert tid in topics
