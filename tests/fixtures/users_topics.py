"""Test fixtures for users.topics redesign and migration scenarios."""

import pytest
from uuid import uuid4, UUID
from typing import List, Dict, Any


# ============================================================================
# Sample Topic IDs for Migration Tests
# ============================================================================


@pytest.fixture
def topic_ids_for_migration() -> List[str]:
    """Generate sample topic UUIDs for migration testing.

    Returns:
        List of 10 unique topic UUID strings for migration scenarios.
    """
    return [str(uuid4()) for _ in range(10)]


# ============================================================================
# User Fixtures - Representative Topic Patterns
# ============================================================================


@pytest.fixture
def user_with_empty_topics() -> Dict[str, Any]:
    """User with empty topics array and default flags.

    Use case: New user, no topic subscriptions yet.

    Returns:
        Dict with user fields: topics=[], enable_feishu=True, enable_email=True
    """
    return {
        "id": str(uuid4()),
        "name": "Empty Topics User",
        "email": "empty@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "topics": [],
        "enable_feishu": True,
        "enable_email": True,
    }


@pytest.fixture
def user_with_single_topic() -> Dict[str, Any]:
    """User with exactly one topic ID.

    Use case: Minimal valid subscription scenario.

    Returns:
        Dict with user fields: topics=[single_uuid], default flags
    """
    return {
        "id": str(uuid4()),
        "name": "Single Topic User",
        "email": "single@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "topics": [str(uuid4())],
        "enable_feishu": True,
        "enable_email": True,
    }


@pytest.fixture
def user_with_multiple_topics() -> Dict[str, Any]:
    """User with 5+ topic IDs (typical scenario).

    Use case: Standard user with multiple topic subscriptions.

    Returns:
        Dict with user fields: topics=[5_uuids], default flags
    """
    return {
        "id": str(uuid4()),
        "name": "Multiple Topics User",
        "email": "multiple@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "topics": [str(uuid4()) for _ in range(5)],
        "enable_feishu": True,
        "enable_email": True,
    }


@pytest.fixture
def user_with_max_topics() -> Dict[str, Any]:
    """User with exactly 100 topic IDs (boundary case).

    Use case: Maximum allowed topics per user.

    Returns:
        Dict with user fields: topics=[100_uuids], default flags
    """
    return {
        "id": str(uuid4()),
        "name": "Max Topics User",
        "email": "max@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "topics": [str(uuid4()) for _ in range(100)],
        "enable_feishu": True,
        "enable_email": True,
    }


# ============================================================================
# User Fixtures - Channel Flag Variations
# ============================================================================


@pytest.fixture
def user_with_disabled_feishu() -> Dict[str, Any]:
    """User with Feishu notifications disabled.

    Use case: Email-only notification preference.

    Returns:
        Dict with user fields: enable_feishu=False, enable_email=True
    """
    return {
        "id": str(uuid4()),
        "name": "Feishu Disabled User",
        "email": "no-feishu@example.com",
        "feishu_webhook_url": None,
        "feishu_webhook_secret": None,
        "topics": [str(uuid4()) for _ in range(3)],
        "enable_feishu": False,
        "enable_email": True,
    }


@pytest.fixture
def user_with_disabled_email() -> Dict[str, Any]:
    """User with email notifications disabled.

    Use case: Feishu-only notification preference.

    Returns:
        Dict with user fields: enable_feishu=True, enable_email=False
    """
    return {
        "id": str(uuid4()),
        "name": "Email Disabled User",
        "email": "no-email@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "topics": [str(uuid4()) for _ in range(3)],
        "enable_feishu": True,
        "enable_email": False,
    }


# ============================================================================
# Edge Case Fixtures
# ============================================================================


@pytest.fixture
def user_with_duplicate_topics() -> Dict[str, Any]:
    """User with duplicate topic IDs (INVALID - for validation testing).

    Use case: Test duplicate detection in Pydantic validator.

    Returns:
        Dict with duplicate UUIDs in topics array
    """
    duplicate_id = str(uuid4())
    return {
        "id": str(uuid4()),
        "name": "Duplicate Topics User",
        "email": "duplicate@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "topics": [duplicate_id, duplicate_id, str(uuid4())],
        "enable_feishu": True,
        "enable_email": True,
    }


@pytest.fixture
def user_with_invalid_uuid() -> Dict[str, Any]:
    """User with non-UUID strings in topics (INVALID - for validation testing).

    Use case: Test UUID format validation in Pydantic validator.

    Returns:
        Dict with invalid UUID strings in topics array
    """
    return {
        "id": str(uuid4()),
        "name": "Invalid UUID User",
        "email": "invalid-uuid@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "topics": ["not-a-uuid", "also-not-uuid", str(uuid4())],
        "enable_feishu": True,
        "enable_email": True,
    }


@pytest.fixture
def user_exceeding_max_topics() -> Dict[str, Any]:
    """User with 101 topic IDs (INVALID - for boundary testing).

    Use case: Test max count validation (should reject with error).

    Returns:
        Dict with 101 UUIDs in topics array (exceeds max_length=100)
    """
    return {
        "id": str(uuid4()),
        "name": "Exceeded Max User",
        "email": "exceeded@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "topics": [str(uuid4()) for _ in range(101)],
        "enable_feishu": True,
        "enable_email": True,
    }


@pytest.fixture
def user_with_all_channels_disabled() -> Dict[str, Any]:
    """User with both notification channels disabled (edge case).

    Use case: Test soft warning when no channels enabled.

    Returns:
        Dict with enable_feishu=False, enable_email=False
    """
    return {
        "id": str(uuid4()),
        "name": "No Channels User",
        "email": "no-channels@example.com",
        "feishu_webhook_url": None,
        "feishu_webhook_secret": None,
        "topics": [str(uuid4())],
        "enable_feishu": False,
        "enable_email": False,
    }


# ============================================================================
# Migration Scenario Fixtures
# ============================================================================


@pytest.fixture
def migration_scenario_multiple_subs() -> Dict[str, Any]:
    """Pre-migration user with multiple subscriptions (for migration logic testing).

    Use case: Simulate legacy subscription data before migration.

    Returns:
        Dict with subscriptions array (legacy format)
    """
    return {
        "id": str(uuid4()),
        "name": "Migration User",
        "email": "migration@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "subscriptions": [
            {
                "topic_id": str(uuid4()),
                "enable_feishu": True,
                "enable_email": False,
            },
            {
                "topic_id": str(uuid4()),
                "enable_feishu": False,
                "enable_email": True,
            },
            {
                "topic_id": str(uuid4()),
                "enable_feishu": True,
                "enable_email": True,
            },
        ],
    }


@pytest.fixture
def expected_migrated_user() -> Dict[str, Any]:
    """Expected post-migration user format.

    Use case: Validate migration correctness.

    Returns:
        Dict with topics array and aggregated channel flags
    """
    return {
        "id": str(uuid4()),
        "name": "Migrated User",
        "email": "migrated@example.com",
        "feishu_webhook_url": "https://example.com/webhook",
        "feishu_webhook_secret": "secret123",
        "topics": [str(uuid4()) for _ in range(3)],
        "enable_feishu": True,  # OR of subscription flags
        "enable_email": True,  # OR of subscription flags
    }
