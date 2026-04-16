"""Packaging and import tests proving twx has no legacy dependencies."""

import os


def test_cli_runner_imports_without_legacy_db_env(monkeypatch):
    """twx imports cleanly without DATABASE_URL or other legacy env vars."""
    # Remove legacy env vars that the old stack required
    for var in ["DATABASE_URL", "REDIS_URL", "CELERY_BROKER_URL"]:
        monkeypatch.delenv(var, raising=False)
        assert var not in os.environ

    from twx.cli import cli

    assert cli is not None


def test_config_reads_twitter_api_key(monkeypatch):
    """Settings reads TWITTER_API_KEY from environment."""
    monkeypatch.setenv("TWITTER_API_KEY", "test-key-123")

    from twx.config import Settings

    settings = Settings()
    assert settings.api_key == "test-key-123"


def test_config_raises_on_missing_api_key(monkeypatch):
    """Settings.require_api_key raises ConfigError when key is absent."""
    monkeypatch.delenv("TWITTER_API_KEY", raising=False)

    import pytest

    from twx.config import Settings
    from twx.errors import ConfigError

    settings = Settings()

    with pytest.raises(ConfigError):
        _ = settings.require_api_key()


def test_models_import_without_legacy_deps():
    """All twx models can be imported without any legacy packages."""
    from twx.models import (
        ErrorEnvelope,
        NormalizedMedia,
        NormalizedMetrics,
        NormalizedTweet,
        NormalizedUser,
        SuccessEnvelope,
    )

    assert NormalizedMedia is not None
    assert NormalizedMetrics is not None
    assert NormalizedTweet is not None
    assert NormalizedUser is not None
    assert SuccessEnvelope is not None
    assert ErrorEnvelope is not None


def test_errors_import_without_legacy_deps():
    """All twx error classes can be imported without legacy packages."""
    from twx.errors import ConfigError, TWXError, TransformError, UpstreamError

    assert issubclass(ConfigError, TWXError)
    assert issubclass(UpstreamError, TWXError)
    assert issubclass(TransformError, TWXError)


def test_package_version():
    """twx package exports __version__."""
    from twx import __version__

    assert __version__
    assert isinstance(__version__, str)
