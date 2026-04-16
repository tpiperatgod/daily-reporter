"""Tests for the twitterapi.io HTTP client."""

from typing import cast

import httpx
import pytest

from twx.client import TwitterApiClient
from twx.errors import UpstreamError


def test_user_tweets_request_sends_api_key_and_username():
    """Client sends X-API-Key header and userName param."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    client = TwitterApiClient(api_key="test-key", transport=transport)
    client.get_user_tweets(username="karpathy")

    headers = cast(dict[str, str], seen["headers"])
    url = cast(str, seen["url"])

    assert headers["x-api-key"] == "test-key"
    assert "userName=karpathy" in url


def test_user_tweets_with_cursor():
    """Client passes cursor parameter when provided."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    client = TwitterApiClient(api_key="test", transport=transport)
    client.get_user_tweets(username="karpathy", cursor="abc123")

    url = cast(str, seen["url"])

    assert "cursor=abc123" in url


def test_user_tweets_with_include_replies():
    """Client passes includeReplies when true."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    client = TwitterApiClient(api_key="test", transport=transport)
    client.get_user_tweets(username="karpathy", include_replies=True)

    url = cast(str, seen["url"])

    assert "includeReplies" in url


def test_search_tweets_sends_query_and_mode():
    """Search sends query and queryType params."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    client = TwitterApiClient(api_key="test", transport=transport)
    client.get_search_tweets(query="AI agents", mode="top")

    url = cast(str, seen["url"])

    assert "query=AI" in url
    assert "queryType=Top" in url


def test_search_tweets_latest_mode():
    """Latest mode sends queryType=Latest."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    client = TwitterApiClient(api_key="test", transport=transport)
    client.get_search_tweets(query="test", mode="latest")

    url = cast(str, seen["url"])

    assert "queryType=Latest" in url


def test_rate_limit_raises_upstream_error():
    """429 response raises retryable UpstreamError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    transport = httpx.MockTransport(handler)
    client = TwitterApiClient(api_key="test", transport=transport)

    with pytest.raises(UpstreamError) as exc_info:
        client.get_user_tweets(username="test")

    assert exc_info.value.retryable is True
    assert "Rate limited" in str(exc_info.value)


def test_server_error_raises_upstream_error():
    """5xx response raises retryable UpstreamError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    client = TwitterApiClient(api_key="test", transport=transport)

    with pytest.raises(UpstreamError) as exc_info:
        client.get_user_tweets(username="test")

    assert exc_info.value.retryable is True


def test_client_error_raises_non_retryable():
    """4xx (non-429) response raises non-retryable UpstreamError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    transport = httpx.MockTransport(handler)
    client = TwitterApiClient(api_key="test", transport=transport)

    with pytest.raises(UpstreamError) as exc_info:
        client.get_user_tweets(username="test")

    assert exc_info.value.retryable is False
