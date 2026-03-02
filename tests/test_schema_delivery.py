"""Tests for DeliveryResponse schema compatibility with both digest types.

Regression tests ensuring schemas can parse deliveries from both:
- Topic-scoped digests (digest_id set, user_digest_id null)
- User-scoped digests (user_digest_id set, digest_id null)
"""

from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import MagicMock

from app.api.schemas import DeliveryResponse as APIDeliveryResponse
class TestAPIDeliveryResponseSchema:
    """Test API DeliveryResponse schema parses both digest types."""

    def test_parses_topic_digest_delivery(self):
        """
        Verify API DeliveryResponse accepts topic-scoped delivery.

        Topic deliveries have:
        - digest_id: non-null UUID
        - user_digest_id: null
        """
        digest_id = uuid4()
        user_id = uuid4()
        delivery_id = uuid4()
        now = datetime.now(UTC)

        # Create mock ORM object simulating topic-digest delivery
        mock_delivery = MagicMock()
        mock_delivery.id = delivery_id
        mock_delivery.digest_id = digest_id
        mock_delivery.user_digest_id = None
        mock_delivery.user_id = user_id
        mock_delivery.channel = "feishu"
        mock_delivery.status = "success"
        mock_delivery.retry_count = 0
        mock_delivery.error_msg = None
        mock_delivery.sent_at = now
        mock_delivery.created_at = now

        # Parse via Pydantic schema
        response = APIDeliveryResponse.model_validate(mock_delivery)

        # Verify all fields parsed correctly
        assert response.id == delivery_id
        assert response.digest_id == digest_id
        assert response.user_digest_id is None
        assert response.user_id == user_id
        assert response.channel == "feishu"
        assert response.status == "success"

    def test_parses_user_digest_delivery(self):
        """
        Verify API DeliveryResponse accepts user-scoped delivery.

        User deliveries have:
        - digest_id: null
        - user_digest_id: non-null UUID
        """
        user_digest_id = uuid4()
        user_id = uuid4()
        delivery_id = uuid4()
        now = datetime.now(UTC)

        # Create mock ORM object simulating user-digest delivery
        mock_delivery = MagicMock()
        mock_delivery.id = delivery_id
        mock_delivery.digest_id = None
        mock_delivery.user_digest_id = user_digest_id
        mock_delivery.user_id = user_id
        mock_delivery.channel = "email"
        mock_delivery.status = "pending"
        mock_delivery.retry_count = 1
        mock_delivery.error_msg = "retry scheduled"
        mock_delivery.sent_at = None
        mock_delivery.created_at = now

        # Parse via Pydantic schema
        response = APIDeliveryResponse.model_validate(mock_delivery)

        # Verify all fields parsed correctly
        assert response.id == delivery_id
        assert response.digest_id is None
        assert response.user_digest_id == user_digest_id
        assert response.user_id == user_id
        assert response.channel == "email"
        assert response.status == "pending"

    def test_both_fields_optional_but_one_required(self):
        """
        Verify schema allows both fields to be optional at Pydantic level.

        Note: The DB has a CHECK constraint ensuring exactly one is non-null,
        but Pydantic schema allows both to be Optional for flexibility.
        This test verifies the schema accepts valid payloads.
        """
        delivery_id = uuid4()
        user_id = uuid4()
        digest_id = uuid4()
        now = datetime.now(UTC)

        # Test with digest_id only
        mock_topic_delivery = MagicMock()
        mock_topic_delivery.id = delivery_id
        mock_topic_delivery.digest_id = digest_id
        mock_topic_delivery.user_digest_id = None
        mock_topic_delivery.user_id = user_id
        mock_topic_delivery.channel = "feishu"
        mock_topic_delivery.status = "success"
        mock_topic_delivery.retry_count = 0
        mock_topic_delivery.error_msg = None
        mock_topic_delivery.sent_at = now
        mock_topic_delivery.created_at = now

        response1 = APIDeliveryResponse.model_validate(mock_topic_delivery)
        assert response1.digest_id == digest_id
        assert response1.user_digest_id is None

        # Test with user_digest_id only
        user_digest_id = uuid4()
        mock_user_delivery = MagicMock()
        mock_user_delivery.id = delivery_id
        mock_user_delivery.digest_id = None
        mock_user_delivery.user_digest_id = user_digest_id
        mock_user_delivery.user_id = user_id
        mock_user_delivery.channel = "email"
        mock_user_delivery.status = "success"
        mock_user_delivery.retry_count = 0
        mock_user_delivery.error_msg = None
        mock_user_delivery.sent_at = now
        mock_user_delivery.created_at = now

        response2 = APIDeliveryResponse.model_validate(mock_user_delivery)
        assert response2.digest_id is None
        assert response2.user_digest_id == user_digest_id



class TestCLIDeliveryResponseSchema:
    """Test CLI DeliveryResponse schema parses both digest types."""

    def test_parses_topic_digest_delivery(self):
        from cli.xndctl.schemas import DeliveryResponse as CLIDeliveryResponse
        
        digest_id = uuid4()
        user_id = uuid4()
        delivery_id = uuid4()
        now = datetime.now(UTC)
        
        mock_delivery = MagicMock()
        mock_delivery.id = delivery_id
        mock_delivery.digest_id = digest_id
        mock_delivery.user_digest_id = None
        mock_delivery.user_id = user_id
        mock_delivery.channel = "feishu"
        mock_delivery.status = "success"
        mock_delivery.retry_count = 0
        mock_delivery.error_msg = None
        mock_delivery.sent_at = now
        mock_delivery.created_at = now
        
        response = CLIDeliveryResponse.model_validate(mock_delivery)
        
        assert response.id == delivery_id
        assert response.digest_id == digest_id
        assert response.user_digest_id is None
        assert response.user_id == user_id
        assert response.channel == "feishu"
        assert response.status == "success"

    def test_parses_user_digest_delivery(self):
        from cli.xndctl.schemas import DeliveryResponse as CLIDeliveryResponse
        
        user_digest_id = uuid4()
        user_id = uuid4()
        delivery_id = uuid4()
        now = datetime.now(UTC)
        
        mock_delivery = MagicMock()
        mock_delivery.id = delivery_id
        mock_delivery.digest_id = None
        mock_delivery.user_digest_id = user_digest_id
        mock_delivery.user_id = user_id
        mock_delivery.channel = "email"
        mock_delivery.status = "pending"
        mock_delivery.retry_count = 1
        mock_delivery.error_msg = "retry scheduled"
        mock_delivery.sent_at = None
        mock_delivery.created_at = now
        
        response = CLIDeliveryResponse.model_validate(mock_delivery)
        
        assert response.id == delivery_id
        assert response.digest_id is None
        assert response.user_digest_id == user_digest_id
        assert response.user_id == user_id
        assert response.channel == "email"
        assert response.status == "pending"