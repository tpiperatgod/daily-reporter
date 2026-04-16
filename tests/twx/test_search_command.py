"""Contract tests for the twx search command."""

import json
from collections.abc import Mapping

import httpx


SAMPLE_SEARCH_PAYLOAD = {
    "data": [
        {
            "id": 200,
            "text": "AI agents are the future",
            "url": "https://x.com/user1/status/200",
            "createdAt": "2026-04-15T14:00:00+00:00",
            "author": {"userName": "user1", "name": "User One"},
            "likes": 50,
            "retweets": 10,
            "replies": 5,
            "views": 1000,
        },
        {
            "id": 201,
            "text": "Building with AI agents",
            "url": "https://x.com/user2/status/201",
            "createdAt": "2026-04-15T13:00:00+00:00",
            "author": {"userName": "user2", "name": "User Two"},
            "likes": 30,
            "retweets": 8,
            "replies": 2,
            "views": 500,
        },
        {
            "id": 202,
            "text": "More about AI agents",
            "url": "https://x.com/user3/status/202",
            "createdAt": "2026-04-15T12:00:00+00:00",
            "author": {"userName": "user3", "name": "User Three"},
            "likes": 15,
            "retweets": 3,
            "replies": 1,
            "views": 300,
        },
    ]
}


def _make_transport(payload: Mapping[str, object], status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return httpx.MockTransport(handler)


def test_search_command_emits_normalized_stdout_json():
    """twx search emits a valid SuccessEnvelope with normalized tweets."""
    from twx.client import TwitterApiClient
    from twx.commands.search import fetch_search_tweets

    transport = _make_transport(SAMPLE_SEARCH_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_search_tweets(
        client=client,
        query="AI agents",
        mode="top",
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["ok"] is True
    assert output["query"]["command"] == "search"
    assert output["query"]["query"] == "AI agents"
    assert output["query"]["mode"] == "top"


def test_search_command_respects_limit():
    """twx search --limit caps the number of returned tweets."""
    from twx.client import TwitterApiClient
    from twx.commands.search import fetch_search_tweets

    transport = _make_transport(SAMPLE_SEARCH_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_search_tweets(
        client=client,
        query="AI agents",
        mode="latest",
        limit=2,
    )
    output = json.loads(envelope.model_dump_json())
    assert len(output["data"]["tweets"]) <= 2


def test_search_command_includes_raw_payload_when_requested():
    """twx search --raw includes the raw upstream payload."""
    from twx.client import TwitterApiClient
    from twx.commands.search import fetch_search_tweets

    transport = _make_transport(SAMPLE_SEARCH_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_search_tweets(
        client=client,
        query="AI agents",
        mode="latest",
        include_raw=True,
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["raw"] is not None
    assert "data" in output["raw"]


def test_search_command_raw_is_none_by_default():
    """Raw is not included unless --raw is passed."""
    from twx.client import TwitterApiClient
    from twx.commands.search import fetch_search_tweets

    transport = _make_transport(SAMPLE_SEARCH_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_search_tweets(
        client=client,
        query="AI agents",
        mode="latest",
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["raw"] is None


def test_search_command_query_metadata():
    """Success envelope includes full query metadata."""
    from twx.client import TwitterApiClient
    from twx.commands.search import fetch_search_tweets

    transport = _make_transport(SAMPLE_SEARCH_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_search_tweets(
        client=client,
        query="AI agents",
        mode="top",
        limit=10,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["query"]["command"] == "search"
    assert output["query"]["query"] == "AI agents"
    assert output["query"]["mode"] == "top"
    assert output["query"]["limit"] == 10
    assert output["meta"]["count"] == len(output["data"]["tweets"])


def test_search_command_handles_empty_results():
    """Empty search results return valid envelope with empty tweets."""
    from twx.client import TwitterApiClient
    from twx.commands.search import fetch_search_tweets

    transport = _make_transport({"data": []})
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_search_tweets(
        client=client,
        query="nonexistent",
        mode="latest",
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["ok"] is True
    assert output["data"]["tweets"] == []
    assert output["meta"]["count"] == 0
