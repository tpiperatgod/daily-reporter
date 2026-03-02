"""Tests for user API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import router
from app.db.models import User, Subscription, Topic


@pytest.fixture
def app():
    """Create FastAPI app with users router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    """Create mock user with subscriptions."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.name = "Test User"
    user.email = "test@example.com"

    # Create mock subscriptions
    sub1 = MagicMock(spec=Subscription)
    sub1.topic = MagicMock(spec=Topic)
    sub1.topic.id = uuid4()
    sub1.topic.name = "Topic 1"

    sub2 = MagicMock(spec=Subscription)
    sub2.topic = MagicMock(spec=Topic)
    sub2.topic.id = uuid4()
    sub2.topic.name = "Topic 2"

    user.subscriptions = [sub1, sub2]
    return user


class TestTriggerUserCollection:
    """Test POST /users/{user_id}/trigger endpoint."""

    @patch("app.api.users.get_entity_or_404")
    @patch("app.api.users.celery_app")
    def test_trigger_user_collection_success(self, mock_celery_app, mock_get_entity, client, mock_user):
        """Test successful user collection trigger."""
        # Setup mocks
        mock_get_entity.return_value = mock_user
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery_app.send_task.return_value = mock_task

        # Make request
        response = client.post(f"/users/{mock_user.id}/trigger")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "User topic collection triggered"
        assert data["task_id"] == "test-task-id"
        assert data["user_id"] == str(mock_user.id)
        assert data["topic_count"] == 2

        # Verify Celery task was called
        mock_celery_app.send_task.assert_called_once_with(
            "app.workers.tasks.collect_user_topics",
            args=[str(mock_user.id)],
        )

    @patch("app.api.users.get_entity_or_404")
    def test_trigger_user_collection_no_subscriptions(self, mock_get_entity, client, mock_user):
        """Test trigger fails when user has no subscriptions."""
        # Setup user with no subscriptions
        mock_user.subscriptions = []
        mock_get_entity.return_value = mock_user

        # Make request
        response = client.post(f"/users/{mock_user.id}/trigger")

        # Assertions
        assert response.status_code == 400
        assert "no topic subscriptions" in response.json()["detail"].lower()

    @patch("app.api.users.get_entity_or_404")
    def test_trigger_user_collection_user_not_found(self, mock_get_entity, client):
        """Test trigger fails when user not found."""
        from fastapi import HTTPException

        # Setup mock to raise 404
        user_id = uuid4()
        mock_get_entity.side_effect = HTTPException(status_code=404, detail="User not found")

        # Make request
        response = client.post(f"/users/{user_id}/trigger")

        # Assertions
        assert response.status_code == 404
