"""HTTP API client for xndctl CLI."""

from typing import Any, Dict, Optional
from uuid import UUID
import httpx
from xndctl.config import Config
from xndctl.schemas import (
    UserCreate, UserUpdate, UserResponse, UserWithTopics,
    TopicCreate, TopicUpdate, TopicResponse, TopicWithStats,
    DigestWithDetails,
    TriggerResponse, UserTriggerResponse, SendDigestResponse,
    PaginatedResponse,
)



class APIError(Exception):
    """Base exception for API errors."""
    pass


class NotFoundError(APIError):
    """Resource not found error."""
    pass


class ValidationError(APIError):
    """Request validation error."""
    pass


class APIClient:
    """HTTP client for X News Digest API."""

    def __init__(self, config: Config):
        """Initialize API client."""
        self.config = config
        self.base_url = config.api.base_url.rstrip("/")
        self.timeout = config.api.timeout
        self.verify_ssl = config.api.verify_ssl

    def _get_client(self) -> httpx.Client:
        """Get HTTP client instance."""
        return httpx.Client(
            timeout=self.timeout,
            verify=self.verify_ssl
        )

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle HTTP response and errors."""
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                try:
                    error_detail = e.response.json().get("detail", "Resource not found")
                except Exception:
                    error_detail = "Resource not found"
                raise NotFoundError(error_detail)
            elif e.response.status_code == 422:
                try:
                    error_detail = e.response.json().get("detail", "Validation error")
                except Exception:
                    error_detail = "Validation error"
                raise ValidationError(str(error_detail))
            else:
                try:
                    error_detail = e.response.json().get("detail", str(e))
                except Exception:
                    error_detail = str(e)
                raise APIError(f"HTTP {e.response.status_code}: {error_detail}")
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {str(e)}")

    # ========================================================================
    # User Operations
    # ========================================================================

    def create_user(self, user: UserCreate) -> UserResponse:
        """Create a new user."""
        with self._get_client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/users",
                json=user.model_dump(exclude_none=True)
            )
            data = self._handle_response(response)
            return UserResponse(**data)

    def list_users(self, limit: int = 100, offset: int = 0) -> PaginatedResponse:
        """List users with pagination."""
        with self._get_client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/users",
                params={"limit": limit, "offset": offset}
            )
            data = self._handle_response(response)
            data["items"] = [UserWithTopics(**item) for item in data["items"]]
            return PaginatedResponse(**data)
    def get_user(self, user_id: UUID) -> UserWithTopics:
        """Get user by ID."""
        with self._get_client() as client:
            response = client.get(f"{self.base_url}/api/v1/users/{user_id}")
            data = self._handle_response(response)
            return UserWithTopics(**data)
    def update_user(self, user_id: UUID, user: UserUpdate) -> UserResponse:
        """Update user."""
        with self._get_client() as client:
            response = client.patch(
                f"{self.base_url}/api/v1/users/{user_id}",
                json=user.model_dump(exclude_none=True)
            )
            data = self._handle_response(response)
            return UserResponse(**data)

    def delete_user(self, user_id: UUID) -> None:
        """Delete user."""
        with self._get_client() as client:
            response = client.delete(f"{self.base_url}/api/v1/users/{user_id}")
            self._handle_response(response)

    def find_user_by_name(self, name: str) -> Optional[UserWithTopics]:
        """Find user by name (returns first match)."""
        users = self.list_users(limit=1000)  # Get all users
        for user in users.items:
            if user.name and user.name.lower() == name.lower():
                return user
        return None
    def find_user_by_email(self, email: str) -> Optional[UserWithTopics]:
        """Find user by email (returns first match)."""
        users = self.list_users(limit=1000)  # Get all users
        for user in users.items:
            if user.email.lower() == email.lower():
                return user
        return None
    # ========================================================================
    # Topic Operations
    # ========================================================================

    def create_topic(self, topic: TopicCreate) -> TopicResponse:
        """Create a new topic."""
        with self._get_client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/topics",
                json=topic.model_dump()
            )
            data = self._handle_response(response)
            return TopicResponse(**data)

    def list_topics(self, limit: int = 100, offset: int = 0) -> PaginatedResponse:
        """List topics with pagination."""
        with self._get_client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/topics",
                params={"limit": limit, "offset": offset}
            )
            data = self._handle_response(response)
            data["items"] = [TopicWithStats(**item) for item in data["items"]]
            return PaginatedResponse(**data)

    def get_topic(self, topic_id: UUID) -> TopicWithStats:
        """Get topic by ID."""
        with self._get_client() as client:
            response = client.get(f"{self.base_url}/api/v1/topics/{topic_id}")
            data = self._handle_response(response)
            return TopicWithStats(**data)

    def update_topic(self, topic_id: UUID, topic: TopicUpdate) -> TopicResponse:
        """Update topic."""
        with self._get_client() as client:
            response = client.patch(
                f"{self.base_url}/api/v1/topics/{topic_id}",
                json=topic.model_dump(exclude_none=True)
            )
            data = self._handle_response(response)
            return TopicResponse(**data)

    def delete_topic(self, topic_id: UUID) -> None:
        """Delete topic."""
        with self._get_client() as client:
            response = client.delete(f"{self.base_url}/api/v1/topics/{topic_id}")
            self._handle_response(response)

    def find_topic_by_name(self, name: str) -> Optional[TopicWithStats]:
        """Find topic by name (returns first match)."""
        topics = self.list_topics(limit=1000)  # Get all topics
        for topic in topics.items:
            if topic.name.lower() == name.lower():
                return topic
        return None

    def trigger_topic(self, topic_id: UUID) -> TriggerResponse:
        """Manually trigger topic collection."""
        with self._get_client() as client:
            response = client.post(f"{self.base_url}/api/v1/topics/{topic_id}/trigger")
            data = self._handle_response(response)
            return TriggerResponse(**data)

    def trigger_user(self, user_id: UUID) -> UserTriggerResponse:
        """Trigger data collection for all topics subscribed by a user.

        Args:
            user_id: UUID of the user

        Returns:
            UserTriggerResponse with task ID and topic count
        """
        with self._get_client() as client:
            response = client.post(f"{self.base_url}/api/v1/users/{user_id}/trigger")
            data = self._handle_response(response)
            return UserTriggerResponse(**data)
    # ========================================================================
    # Digest Operations
    # ========================================================================

    def list_digests(self, limit: int = 100, offset: int = 0) -> PaginatedResponse:
        """List digests with pagination."""
        with self._get_client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/digests",
                params={"limit": limit, "offset": offset}
            )
            data = self._handle_response(response)
            data["items"] = [DigestWithDetails(**item) for item in data["items"]]
            return PaginatedResponse(**data)

    def get_digest(self, digest_id: UUID) -> DigestWithDetails:
        """Get digest by ID."""
        with self._get_client() as client:
            response = client.get(f"{self.base_url}/api/v1/digests/{digest_id}")
            data = self._handle_response(response)
            return DigestWithDetails(**data)

    def send_digest(self, digest_id: UUID, user_id: UUID) -> SendDigestResponse:
        """Manually send digest to a user.

        Args:
            digest_id: UUID of the digest to send
            user_id: UUID of the user to send to

        Returns:
            SendDigestResponse with delivery statistics
        """
        with self._get_client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/digests/{digest_id}/send",
                json={"user_id": str(user_id)}
            )
            data = self._handle_response(response)
            return SendDigestResponse(**data)
