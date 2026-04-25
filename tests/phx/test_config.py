"""Tests for phx.config.Settings."""

from __future__ import annotations

import pytest

from phx.config import Settings
from phx.errors import ConfigError


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "token-123")
    monkeypatch.delenv("PHX_API_BASE_URL", raising=False)
    monkeypatch.delenv("PHX_DEFAULT_LIMIT", raising=False)

    settings = Settings()

    assert settings.token == "token-123"
    assert settings.base_url == "https://api.producthunt.com/v2/api/graphql"
    assert settings.default_limit == 20


def test_settings_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "token-123")
    monkeypatch.setenv("PHX_API_BASE_URL", "https://ph.test/graphql")
    monkeypatch.setenv("PHX_DEFAULT_LIMIT", "50")

    settings = Settings()

    assert settings.base_url == "https://ph.test/graphql"
    assert settings.default_limit == 50


def test_require_token_raises_when_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PRODUCTHUNT_TOKEN", raising=False)

    settings = Settings()

    with pytest.raises(ConfigError, match="PRODUCTHUNT_TOKEN"):
        settings.require_token()


def test_invalid_default_limit_raises_config_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "token-123")
    monkeypatch.setenv("PHX_DEFAULT_LIMIT", "not-an-int")

    with pytest.raises(ConfigError, match="PHX_DEFAULT_LIMIT"):
        Settings()


def test_default_limit_must_be_positive(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "token-123")
    monkeypatch.setenv("PHX_DEFAULT_LIMIT", "0")

    with pytest.raises(ConfigError, match="PHX_DEFAULT_LIMIT"):
        Settings()
