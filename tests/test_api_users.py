import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.api.users import trigger_user_collection


@dataclass
class _UserStub:
    id: UUID
    name: str
    email: str
    topics: list[str]
    enable_feishu: bool
    enable_email: bool
    feishu_webhook_url: str


def _make_user(*, topic_count: int) -> _UserStub:
    return _UserStub(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        topics=[str(uuid4()) for _ in range(topic_count)],
        enable_feishu=True,
        enable_email=True,
        feishu_webhook_url="https://example.com/webhook",
    )


def _setup_successful_dispatch(mock_celery_app, mock_get_entity, user: _UserStub) -> None:
    mock_get_entity.return_value = user
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    mock_celery_app.send_task.return_value = mock_task


class TestTriggerUserCollection:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("time_window", "expected_time_window"),
        [
            (None, "24h"),
            ("4h", "4h"),
            ("1d", "24h"),
        ],
    )
    @patch("app.api.users.get_entity_or_404")
    @patch("app.api.users.celery_app")
    async def test_trigger_success_paths(self, mock_celery_app, mock_get_entity, time_window, expected_time_window):
        user = _make_user(topic_count=2)
        _setup_successful_dispatch(mock_celery_app, mock_get_entity, user)

        db = AsyncMock()
        if time_window is None:
            result = await trigger_user_collection(user.id, db)
        else:
            result = await trigger_user_collection(user.id, db, time_window=time_window)

        assert result.status == "success"
        assert result.message == "User topic collection triggered"
        assert result.task_id == "test-task-id"
        assert result.user_id == user.id
        assert result.topic_count == 2
        assert result.time_window == expected_time_window
        mock_celery_app.send_task.assert_called_once_with(
            "app.workers.tasks.collect_user_topics",
            args=[str(user.id), expected_time_window],
        )

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    async def test_trigger_rejects_user_without_topics(self, mock_get_entity):
        user = _make_user(topic_count=0)
        mock_get_entity.return_value = user

        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await trigger_user_collection(user.id, db)

        assert exc_info.value.status_code == 400
        assert "no topics" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("app.api.users.get_entity_or_404")
    async def test_trigger_propagates_user_not_found(self, mock_get_entity):
        user_id = uuid4()
        mock_get_entity.side_effect = HTTPException(status_code=404, detail="User not found")

        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await trigger_user_collection(user_id, db)

        assert exc_info.value.status_code == 404


class TestNoSubscriptionDependencies:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("topic_count", [1, 3, 5])
    @patch("app.api.users.get_entity_or_404")
    @patch("app.api.users.celery_app")
    async def test_trigger_uses_user_topics_array_for_count(self, mock_celery_app, mock_get_entity, topic_count):
        user = _make_user(topic_count=topic_count)
        _setup_successful_dispatch(mock_celery_app, mock_get_entity, user)

        db = AsyncMock()
        result = await trigger_user_collection(user.id, db)

        assert result.status == "success"
        assert result.topic_count == topic_count
        assert result.topic_count == len(user.topics)
