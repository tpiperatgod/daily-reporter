"""Tests for user API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.users import trigger_user_collection
from app.db.models import User


@pytest.fixture
def mock_user():
    """Create mock user with topics array."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.name = "Test User"
    user.email = "test@example.com"

    # Create topic IDs for user.topics array
    topic_id_1 = uuid4()
    topic_id_2 = uuid4()
    user.topics = [str(topic_id_1), str(topic_id_2)]

    # Create channel flags
    user.enable_feishu = True
    user.enable_email = True
    user.feishu_webhook_url = "https://example.com/webhook"

    return user


class TestTriggerUserCollection:
    """Test POST /users/{user_id}/trigger endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    @patch("app.api.users.celery_app")
    async def test_trigger_user_collection_success(self, mock_celery_app, mock_get_entity, mock_user):
        """Test successful user collection trigger."""
        # Setup mocks
        mock_get_entity.return_value = mock_user
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery_app.send_task.return_value = mock_task

        # Create mock db
        mock_db = AsyncMock()

        # Call function directly
        result = await trigger_user_collection(mock_user.id, mock_db)

        # Assertions
        assert result.status == "success"
        assert result.message == "User topic collection triggered"
        assert result.task_id == "test-task-id"
        assert result.user_id == mock_user.id
        assert result.topic_count == 2
        assert result.time_window == "24h"

        # Verify Celery task was called
        mock_celery_app.send_task.assert_called_once_with(
            "app.workers.tasks.collect_user_topics",
            args=[str(mock_user.id), "24h"],
        )

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    @patch("app.api.users.celery_app")
    async def test_trigger_user_collection_custom_time_window(self, mock_celery_app, mock_get_entity, mock_user):
        mock_get_entity.return_value = mock_user
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery_app.send_task.return_value = mock_task

        mock_db = AsyncMock()

        result = await trigger_user_collection(mock_user.id, mock_db, time_window="4h")

        assert result.status == "success"
        assert result.time_window == "4h"
        mock_celery_app.send_task.assert_called_once_with(
            "app.workers.tasks.collect_user_topics",
            args=[str(mock_user.id), "4h"],
        )

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    @patch("app.api.users.celery_app")
    async def test_trigger_user_collection_normalizes_1d(self, mock_celery_app, mock_get_entity, mock_user):
        mock_get_entity.return_value = mock_user
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery_app.send_task.return_value = mock_task

        mock_db = AsyncMock()

        result = await trigger_user_collection(mock_user.id, mock_db, time_window="1d")

        assert result.status == "success"
        assert result.time_window == "24h"
        mock_celery_app.send_task.assert_called_once_with(
            "app.workers.tasks.collect_user_topics",
            args=[str(mock_user.id), "24h"],
        )

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    async def test_trigger_user_collection_no_topics(self, mock_get_entity, mock_user):
        """Test trigger fails when user has no topics."""
        # Setup user with no topics
        mock_user.topics = []
        mock_get_entity.return_value = mock_user

        # Create mock db
        mock_db = AsyncMock()

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await trigger_user_collection(mock_user.id, mock_db)

        # Assertions
        assert exc_info.value.status_code == 400
        assert "no topics" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    async def test_trigger_user_collection_user_not_found(self, mock_get_entity):
        """Test trigger fails when user not found."""
        # Setup mock to raise 404
        user_id = uuid4()
        mock_get_entity.side_effect = HTTPException(status_code=404, detail="User not found")

        # Create mock db
        mock_db = AsyncMock()

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await trigger_user_collection(user_id, mock_db)

        # Assertions
        assert exc_info.value.status_code == 404


# =============================================================================
# Sentinel Tests - Ensure No Regression to Subscription Assumptions
# =============================================================================


class TestNoSubscriptionDependencies:
    """Sentinel tests ensuring no hard dependency on removed Subscription model."""

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    @patch("app.api.users.celery_app")
    async def test_trigger_uses_topics_array_not_subscriptions(self, mock_celery_app, mock_get_entity):
        """Test that trigger endpoint reads from user.topics array, not subscriptions."""
        user_id = uuid4()

        # Create user with topics array
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.topics = [str(uuid4()), str(uuid4()), str(uuid4())]

        mock_get_entity.return_value = mock_user
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery_app.send_task.return_value = mock_task

        # Create mock db
        mock_db = AsyncMock()

        # Call function directly
        result = await trigger_user_collection(user_id, mock_db)

        # Verify success
        assert result.status == "success"
        assert result.topic_count == 3

        # Verify user.topics was accessed
        assert hasattr(mock_user, "topics")
        assert len(mock_user.topics) == 3

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    async def test_trigger_rejects_empty_topics_list(self, mock_get_entity):
        """Test that trigger fails when user.topics is empty."""
        user_id = uuid4()

        # Create user with empty topics array
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.topics = []

        mock_get_entity.return_value = mock_user

        # Create mock db
        mock_db = AsyncMock()

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await trigger_user_collection(user_id, mock_db)

        # Verify rejection
        assert exc_info.value.status_code == 400
        assert "no topics" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    @patch("app.api.users.celery_app")
    async def test_trigger_topic_count_matches_user_topics_length(self, mock_celery_app, mock_get_entity):
        """Test that topic_count in response matches length of user.topics array."""
        user_id = uuid4()

        # Create user with 5 topics
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.topics = [str(uuid4()) for _ in range(5)]

        mock_get_entity.return_value = mock_user
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery_app.send_task.return_value = mock_task

        # Create mock db
        mock_db = AsyncMock()

        # Call function directly
        result = await trigger_user_collection(user_id, mock_db)

        # Verify topic_count matches
        assert result.status == "success"
        assert result.topic_count == 5
        assert result.topic_count == len(mock_user.topics)

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    @patch("app.api.users.celery_app")
    async def test_trigger_with_single_topic(self, mock_celery_app, mock_get_entity):
        """Test trigger with user having exactly one topic."""
        user_id = uuid4()
        topic_id = uuid4()

        # Create user with single topic
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.topics = [str(topic_id)]

        mock_get_entity.return_value = mock_user
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery_app.send_task.return_value = mock_task

        # Create mock db
        mock_db = AsyncMock()

        # Call function directly
        result = await trigger_user_collection(user_id, mock_db)

        # Verify success with single topic
        assert result.status == "success"
        assert result.topic_count == 1
        assert result.topic_count == len(mock_user.topics)
