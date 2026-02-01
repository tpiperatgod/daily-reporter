from app.services.provider.base import BaseProvider
from app.services.provider.mock_adapter import MockAdapter
from app.services.provider.twitter_adapter import TwitterAPIAdapter
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_provider() -> BaseProvider:
    """
    Factory function to get the appropriate provider instance.

    Returns the provider based on the X_PROVIDER setting:
    - "TWITTER_API": Returns TwitterAPIAdapter (requires TWITTER_API_KEY)
    - "MOCK" or default: Returns MockAdapter for development/testing

    Returns:
        BaseProvider: Provider instance

    Raises:
        ValueError: If provider is requested but required credentials are not set
    """
    provider_type = settings.X_PROVIDER.upper()

    logger.info(f"Initializing provider: {provider_type}")

    if provider_type == "TWITTER_API":
        try:
            return TwitterAPIAdapter()
        except ValueError as e:
            logger.error(f"Failed to initialize TwitterAPIAdapter: {e}")
            raise

    # Default to Mock adapter
    logger.info("Using Mock adapter for data collection")
    return MockAdapter()


__all__ = ["get_provider"]
