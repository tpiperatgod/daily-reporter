import os

import pytest

from tests.environment_contract import TestEnvironmentContract


def _should_enforce_test_contract() -> bool:
    return os.getenv("XND_ENFORCE_TEST_CONTRACT") == "1" or os.getenv("ENVIRONMENT") == "test"


@pytest.fixture(scope="session", autouse=True)
def verify_test_environment() -> None:
    if not _should_enforce_test_contract():
        return
    TestEnvironmentContract().assert_valid()
