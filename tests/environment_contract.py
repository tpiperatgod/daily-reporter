from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse


@dataclass(frozen=True)
class ContractResult:
    ok: bool
    errors: list[str]


class TestEnvironmentContract:
    __test__ = False

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        self._environ = dict(os.environ if environ is None else environ)

    def verify_all(self) -> ContractResult:
        errors: list[str] = []

        database_url = self._environ.get("DATABASE_URL", "")
        redis_url = self._environ.get("REDIS_URL", "")
        environment = self._environ.get("ENVIRONMENT", "")
        provider = self._environ.get("X_PROVIDER", "")

        if not self._is_test_database(database_url):
            errors.append("DATABASE_URL must target database xnews_digest_test")
        if not self._is_test_redis(redis_url):
            errors.append("REDIS_URL must target redis database /1")
        if environment != "test":
            errors.append("ENVIRONMENT must be test")
        if provider != "MOCK":
            errors.append("X_PROVIDER must be MOCK")

        return ContractResult(ok=not errors, errors=errors)

    def assert_valid(self) -> None:
        result = self.verify_all()
        if not result.ok:
            raise RuntimeError("Test environment contract violated: " + "; ".join(result.errors))

    @staticmethod
    def _is_test_database(url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        database_name = (parsed.path or "").rsplit("/", 1)[-1]
        return database_name == "xnews_digest_test"

    @staticmethod
    def _is_test_redis(url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        return (parsed.path or "") == "/1"
