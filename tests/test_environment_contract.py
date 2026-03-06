from tests.environment_contract import TestEnvironmentContract


def _base_env() -> dict[str, str]:
    return {
        "DATABASE_URL": "postgresql+asyncpg://xnews:xnews_password@postgres-test:5432/xnews_digest_test",
        "REDIS_URL": "redis://redis-test:6379/1",
        "ENVIRONMENT": "test",
        "X_PROVIDER": "MOCK",
    }


def test_verify_all_passes_for_isolated_test_env() -> None:
    contract = TestEnvironmentContract(_base_env())
    result = contract.verify_all()
    assert result.ok
    assert result.errors == []


def test_verify_all_fails_for_non_test_database() -> None:
    env = _base_env()
    env["DATABASE_URL"] = "postgresql+asyncpg://xnews:xnews_password@postgres-test:5432/xnews_digest"
    contract = TestEnvironmentContract(env)
    result = contract.verify_all()
    assert not result.ok
    assert any("DATABASE_URL" in error for error in result.errors)


def test_verify_all_fails_for_wrong_redis_db() -> None:
    env = _base_env()
    env["REDIS_URL"] = "redis://redis-test:6379/0"
    contract = TestEnvironmentContract(env)
    result = contract.verify_all()
    assert not result.ok
    assert any("REDIS_URL" in error for error in result.errors)


def test_verify_all_fails_for_wrong_environment_or_provider() -> None:
    env = _base_env()
    env["ENVIRONMENT"] = "dev"
    env["X_PROVIDER"] = "TWITTER_API"
    contract = TestEnvironmentContract(env)
    result = contract.verify_all()
    assert not result.ok
    assert any("ENVIRONMENT" in error for error in result.errors)
    assert any("X_PROVIDER" in error for error in result.errors)


def test_assert_valid_raises_on_violation() -> None:
    env = _base_env()
    env["DATABASE_URL"] = ""
    contract = TestEnvironmentContract(env)

    try:
        contract.assert_valid()
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("assert_valid() should raise RuntimeError for invalid contract")

    assert "Test environment contract violated" in message
