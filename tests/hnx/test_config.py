"""Tests for hnx.config.Settings."""

from __future__ import annotations

import pytest

from hnx.config import Settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HNX_API_BASE_URL", raising=False)
    monkeypatch.delenv("HNX_DEFAULT_LIMIT", raising=False)
    monkeypatch.delenv("HNX_CONCURRENCY", raising=False)

    s = Settings()

    assert s.base_url == "https://hacker-news.firebaseio.com/v0"
    assert s.default_limit == 30
    assert s.concurrency == 10


def test_settings_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HNX_API_BASE_URL", "http://localhost:8000/v0")
    monkeypatch.setenv("HNX_DEFAULT_LIMIT", "5")
    monkeypatch.setenv("HNX_CONCURRENCY", "2")

    s = Settings()

    assert s.base_url == "http://localhost:8000/v0"
    assert s.default_limit == 5
    assert s.concurrency == 2


def test_algolia_base_url_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HNX_ALGOLIA_BASE_URL", raising=False)
    s = Settings()
    assert s.algolia_base_url == "https://hn.algolia.com/api/v1"


def test_algolia_base_url_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HNX_ALGOLIA_BASE_URL", "https://hn.test/api/v1")
    s = Settings()
    assert s.algolia_base_url == "https://hn.test/api/v1"
