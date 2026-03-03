"""Test configuration and fixtures."""

import pytest
import asyncio

# Register fixtures from users_topics module
pytest_plugins = ["tests.fixtures.users_topics"]
