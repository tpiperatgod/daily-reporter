"""
Contract tests for users.topics schema redesign.

These tests validate the canonical schema contract defined in:
.sisyphus/notepads/user-topics-schema-redesign/contract.md

Run with: pytest tests/test_contract_users_topics.py -v
"""

import pytest
from uuid import UUID, uuid4
from pydantic import BaseModel, ValidationError, Field, field_validator
from typing import List, Optional


# ============================================================================
# Schema Definitions (Contract Implementation)
# ============================================================================


class UserCreateContract(BaseModel):
    """Contract schema for creating a user with topics array."""

    name: Optional[str] = Field(None, max_length=255)
    email: str
    feishu_webhook_url: Optional[str] = Field(None, max_length=2048)
    feishu_webhook_secret: Optional[str] = Field(None, max_length=255)
    topics: List[str] = Field(default_factory=list, max_length=100)
    enable_feishu: bool = True
    enable_email: bool = True

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: List[str]) -> List[str]:
        """Validate topics array according to contract rules."""
        # Rule: Maximum 100 topics
        if len(v) > 100:
            raise ValueError("Maximum 100 topics per user exceeded")

        # Track seen UUIDs and errors
        seen = set()
        duplicates = set()
        invalid_uuids = []

        for item in v:
            # Rule: Each item must be valid UUID format
            try:
                UUID(item)
            except (ValueError, AttributeError, TypeError):
                invalid_uuids.append(item)
                continue

            # Rule: No duplicate UUIDs
            if item in seen:
                duplicates.add(item)
            seen.add(item)

        # Report invalid UUIDs first
        if invalid_uuids:
            raise ValueError(f"Invalid UUID format: {invalid_uuids}")

        # Report duplicates
        if duplicates:
            raise ValueError(f"Duplicate topic IDs not allowed: {list(duplicates)}")

        return v


class UserUpdateContract(BaseModel):
    """Contract schema for updating a user with topics array."""

    name: Optional[str] = Field(None, max_length=255)
    feishu_webhook_url: Optional[str] = Field(None, max_length=2048)
    feishu_webhook_secret: Optional[str] = Field(None, max_length=255)
    topics: Optional[List[str]] = Field(None, max_length=100)
    enable_feishu: Optional[bool] = None
    enable_email: Optional[bool] = None

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate topics array according to contract rules."""
        if v is None:
            return v

        # Rule: Maximum 100 topics
        if len(v) > 100:
            raise ValueError("Maximum 100 topics per user exceeded")

        # Track seen UUIDs and errors
        seen = set()
        duplicates = set()
        invalid_uuids = []

        for item in v:
            # Rule: Each item must be valid UUID format
            try:
                UUID(item)
            except (ValueError, AttributeError, TypeError):
                invalid_uuids.append(item)
                continue

            # Rule: No duplicate UUIDs
            if item in seen:
                duplicates.add(item)
            seen.add(item)

        # Report invalid UUIDs first
        if invalid_uuids:
            raise ValueError(f"Invalid UUID format: {invalid_uuids}")

        # Report duplicates
        if duplicates:
            raise ValueError(f"Duplicate topic IDs not allowed: {list(duplicates)}")

        return v


# ============================================================================
# Test Cases: Valid Scenarios
# ============================================================================


class TestValidTopicsContract:
    """Tests for valid topics array scenarios."""

    def test_empty_topics_array_passes(self):
        """Empty topics array should pass with defaults applied."""
        user = UserCreateContract(email="test@example.com")
        assert user.topics == []
        assert user.enable_feishu is True
        assert user.enable_email is True

    def test_single_valid_uuid_passes(self):
        """Single valid UUID should pass."""
        topic_id = str(uuid4())
        user = UserCreateContract(email="test@example.com", topics=[topic_id])
        assert user.topics == [topic_id]

    def test_multiple_valid_uuids_pass(self):
        """Multiple valid UUIDs should pass."""
        topic_ids = [str(uuid4()) for _ in range(5)]
        user = UserCreateContract(email="test@example.com", topics=topic_ids)
        assert user.topics == topic_ids

    def test_max_100_topics_passes(self):
        """Exactly 100 topics should pass (boundary test)."""
        topic_ids = [str(uuid4()) for _ in range(100)]
        user = UserCreateContract(email="test@example.com", topics=topic_ids)
        assert len(user.topics) == 100

    def test_channel_flags_defaults_applied(self):
        """Channel flags should default to True."""
        user = UserCreateContract(email="test@example.com")
        assert user.enable_feishu is True
        assert user.enable_email is True

    def test_channel_flags_explicit_false(self):
        """Channel flags can be explicitly set to False."""
        user = UserCreateContract(email="test@example.com", enable_feishu=False, enable_email=False)
        assert user.enable_feishu is False
        assert user.enable_email is False

    def test_update_with_none_topics_preserves_existing(self):
        """UserUpdate with None topics should not change existing value."""
        update = UserUpdateContract(topics=None)
        assert update.topics is None

    def test_update_with_empty_topics(self):
        """UserUpdate with empty topics array should pass."""
        update = UserUpdateContract(topics=[])
        assert update.topics == []


# ============================================================================
# Test Cases: Invalid Scenarios
# ============================================================================


class TestInvalidUUIDFormat:
    """Tests for invalid UUID format rejection."""

    def test_non_uuid_string_rejected(self):
        """Non-UUID string should be rejected with explicit error."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreateContract(email="test@example.com", topics=["not-a-uuid"])

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Invalid UUID format" in str(errors[0]["msg"])
        assert "not-a-uuid" in str(errors[0]["msg"])

    def test_partial_uuid_rejected(self):
        """Partial UUID should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreateContract(
                email="test@example.com",
                topics=["12345678-1234-1234-1234"],  # Missing last segment
            )

        errors = exc_info.value.errors()
        assert "Invalid UUID format" in str(errors[0]["msg"])

    def test_uuid_with_invalid_characters_rejected(self):
        """UUID with invalid hex characters should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreateContract(
                email="test@example.com",
                topics=["gggggggg-gggg-gggg-gggg-gggggggggggg"],  # Invalid hex
            )

        errors = exc_info.value.errors()
        assert "Invalid UUID format" in str(errors[0]["msg"])

    def test_integer_in_topics_rejected(self):
        """Integer value should be rejected (must be string)."""
        with pytest.raises(ValidationError):
            UserCreateContract(
                email="test@example.com",
                topics=[12345],  # type: ignore
            )

    def test_mixed_valid_and_invalid_uuids(self):
        """Mix of valid and invalid UUIDs should report invalid ones."""
        valid_uuid = str(uuid4())
        with pytest.raises(ValidationError) as exc_info:
            UserCreateContract(email="test@example.com", topics=[valid_uuid, "invalid-uuid", "another-bad"])

        errors = exc_info.value.errors()
        assert "Invalid UUID format" in str(errors[0]["msg"])
        assert "invalid-uuid" in str(errors[0]["msg"])
        assert "another-bad" in str(errors[0]["msg"])


class TestDuplicateUUIDs:
    """Tests for duplicate UUID rejection."""

    def test_duplicate_uuids_rejected(self):
        """Duplicate UUIDs should be rejected with explicit error."""
        topic_id = str(uuid4())
        with pytest.raises(ValidationError) as exc_info:
            UserCreateContract(email="test@example.com", topics=[topic_id, topic_id])

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Duplicate topic IDs not allowed" in str(errors[0]["msg"])
        assert topic_id in str(errors[0]["msg"])

    def test_multiple_duplicates_rejected(self):
        """Multiple duplicate UUIDs should all be reported."""
        topic_id_1 = str(uuid4())
        topic_id_2 = str(uuid4())
        with pytest.raises(ValidationError) as exc_info:
            UserCreateContract(email="test@example.com", topics=[topic_id_1, topic_id_1, topic_id_2, topic_id_2])

        errors = exc_info.value.errors()
        assert "Duplicate topic IDs not allowed" in str(errors[0]["msg"])
        assert topic_id_1 in str(errors[0]["msg"])
        assert topic_id_2 in str(errors[0]["msg"])

    def test_case_sensitivity_of_uuids(self):
        """UUID strings are case-sensitive for deduplication."""
        topic_id = str(uuid4())
        # UUIDs should be compared as strings (case matters)
        lower = topic_id.lower()
        upper = topic_id.upper()

        # These are different strings, so should pass
        user = UserCreateContract(email="test@example.com", topics=[lower, upper])
        assert len(user.topics) == 2


class TestMaxTopicsLimit:
    """Tests for maximum topics limit."""

    def test_exceeds_100_topics_rejected(self):
        topic_ids = [str(uuid4()) for _ in range(101)]
        with pytest.raises(ValidationError) as exc_info:
            UserCreateContract(email="test@example.com", topics=topic_ids)

        errors = exc_info.value.errors()
        assert "100" in str(errors[0]["msg"])

    def test_far_exceeds_limit_rejected(self):
        topic_ids = [str(uuid4()) for _ in range(200)]
        with pytest.raises(ValidationError) as exc_info:
            UserCreateContract(email="test@example.com", topics=topic_ids)

        errors = exc_info.value.errors()
        assert "100" in str(errors[0]["msg"])


class TestChannelFlagsValidation:
    def test_enable_feishu_coerces_truthy(self):
        user = UserCreateContract(email="test@example.com", enable_feishu="true")
        assert user.enable_feishu is True

    def test_enable_email_coerces_one_to_true(self):
        user = UserCreateContract(email="test@example.com", enable_email=1)
        assert user.enable_email is True



# ============================================================================
# Test Cases: No-Compat Constraints
# ============================================================================


class TestNoCompatConstraints:
    """Tests to verify no backward compatibility shims exist."""

    def test_no_subscription_semantics_in_schema(self):
        """Schema should not have subscription-related fields."""
        schema = UserCreateContract.model_json_schema()
        properties = schema.get("properties", {})

        # These fields should NOT exist
        assert "subscription_id" not in properties
        assert "subscriptions" not in properties
        assert "per_topic_channels" not in properties

    def test_topics_is_flat_array(self):
        """topics should be flat array of strings, not objects."""
        schema = UserCreateContract.model_json_schema()
        topics_schema = schema["properties"]["topics"]

        # Should be array type
        assert topics_schema["type"] == "array"

        # Items should be strings (UUID strings), not objects
        assert topics_schema["items"]["type"] == "string"

    def test_channel_flags_are_user_level(self):
        """Channel flags should be at user level, not per-topic."""
        user = UserCreateContract(
            email="test@example.com", topics=[str(uuid4()), str(uuid4())], enable_feishu=True, enable_email=False
        )

        # Channel flags are single values, not per-topic
        assert isinstance(user.enable_feishu, bool)
        assert isinstance(user.enable_email, bool)

        # No way to specify per-topic channels
        assert not hasattr(user, "topic_channels")


# ============================================================================
# Test Cases: Update Schema Specific
# ============================================================================


class TestUserUpdateContract:
    """Tests specific to UserUpdate schema."""

    def test_partial_update_topics_only(self):
        """Can update only topics without other fields."""
        topic_ids = [str(uuid4()) for _ in range(3)]
        update = UserUpdateContract(topics=topic_ids)
        assert update.topics == topic_ids
        assert update.name is None
        assert update.enable_feishu is None

    def test_partial_update_channels_only(self):
        """Can update only channel flags."""
        update = UserUpdateContract(enable_feishu=False)
        assert update.enable_feishu is False
        assert update.topics is None

    def test_update_validates_same_as_create(self):
        """UserUpdate should validate topics same as UserCreate."""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdateContract(topics=["invalid-uuid"])

        assert "Invalid UUID format" in str(exc_info.value)

    def test_update_rejects_duplicates(self):
        """UserUpdate should reject duplicate UUIDs."""
        topic_id = str(uuid4())
        with pytest.raises(ValidationError) as exc_info:
            UserUpdateContract(topics=[topic_id, topic_id])

        assert "Duplicate topic IDs not allowed" in str(exc_info.value)


# ============================================================================
# Integration Test Marker
# ============================================================================


class TestContractIntegration:
    """Integration tests to verify contract end-to-end."""

    @pytest.mark.integration
    def test_full_user_lifecycle_schema(self):
        """Test complete user lifecycle with schema validation."""

        topic_ids = [str(uuid4()) for _ in range(3)]
        user = UserCreateContract(
            name="Test User", email="test@example.com", topics=topic_ids, enable_feishu=True, enable_email=False
        )

        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert len(user.topics) == 3
        assert user.enable_feishu is True
        assert user.enable_email is False


        new_topic_ids = topic_ids + [str(uuid4())]
        update = UserUpdateContract(topics=new_topic_ids)
        assert len(update.topics) == 4  # type: ignore


        channel_update = UserUpdateContract(enable_email=True)
        assert channel_update.enable_email is True
