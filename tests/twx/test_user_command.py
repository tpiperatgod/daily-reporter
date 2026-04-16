"""Contract tests for the twx user command."""

import json
from collections.abc import Mapping

import httpx
import pytest
from click.testing import CliRunner


# ---- Fixtures ----

SAMPLE_TWEETS_PAYLOAD = {
    "data": [
        {
            "id": 100,
            "text": "First tweet",
            "url": "https://x.com/karpathy/status/100",
            "createdAt": "2026-04-15T12:00:00+00:00",
            "author": {"userName": "karpathy", "name": "Andrej Karpathy"},
            "likes": 10,
            "retweets": 2,
            "replies": 1,
            "views": 100,
        },
        {
            "id": 101,
            "text": "Second tweet",
            "url": "https://x.com/karpathy/status/101",
            "createdAt": "2026-04-14T10:00:00+00:00",
            "author": {"userName": "karpathy", "name": "Andrej Karpathy"},
            "likes": 20,
            "retweets": 5,
            "replies": 3,
            "views": 200,
        },
    ]
}


@pytest.fixture()
def fake_user_client():
    """Create a CliRunner with TWITTER_API_KEY set."""
    return CliRunner(env={"TWITTER_API_KEY": "test-key"})


def _make_transport(payload: Mapping[str, object], status_code: int = 200):
    """Create an httpx MockTransport that returns the given payload."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return httpx.MockTransport(handler)


def test_user_command_emits_normalized_stdout_json(fake_user_client):
    """twx user emits a valid SuccessEnvelope with normalized tweets."""
    from twx.commands.user import fetch_user_tweets
    from twx.client import TwitterApiClient

    transport = _make_transport(SAMPLE_TWEETS_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_user_tweets(
        client=client,
        username="karpathy",
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["ok"] is True
    assert output["query"]["command"] == "user"
    assert output["query"]["username"] == "karpathy"
    assert len(output["data"]["tweets"]) == 2


def test_user_command_filters_by_since(fake_user_client):
    """twx user --since filters out tweets before the timestamp."""
    from twx.commands.user import fetch_user_tweets
    from twx.client import TwitterApiClient

    transport = _make_transport(SAMPLE_TWEETS_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_user_tweets(
        client=client,
        username="karpathy",
        since="2026-04-15T00:00:00+00:00",
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    for tweet in output["data"]["tweets"]:
        assert tweet["created_at"] >= "2026-04-15T00:00:00+00:00"


def test_user_command_filters_by_until(fake_user_client):
    """twx user --until filters out tweets after the timestamp."""
    from twx.commands.user import fetch_user_tweets
    from twx.client import TwitterApiClient

    transport = _make_transport(SAMPLE_TWEETS_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_user_tweets(
        client=client,
        username="karpathy",
        until="2026-04-14T12:00:00+00:00",
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    for tweet in output["data"]["tweets"]:
        assert tweet["created_at"] <= "2026-04-14T12:00:00+00:00"


def test_user_command_respects_limit(fake_user_client):
    """twx user --limit caps the number of returned tweets."""
    from twx.commands.user import fetch_user_tweets
    from twx.client import TwitterApiClient

    transport = _make_transport(SAMPLE_TWEETS_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_user_tweets(
        client=client,
        username="karpathy",
        limit=1,
    )
    output = json.loads(envelope.model_dump_json())
    assert len(output["data"]["tweets"]) <= 1


def test_user_command_with_raw_flag(fake_user_client):
    """twx user --raw includes the raw upstream payload."""
    from twx.commands.user import fetch_user_tweets
    from twx.client import TwitterApiClient

    transport = _make_transport(SAMPLE_TWEETS_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_user_tweets(
        client=client,
        username="karpathy",
        include_raw=True,
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["raw"] is not None


def test_user_command_query_metadata(fake_user_client):
    """Success envelope includes query metadata."""
    from twx.commands.user import fetch_user_tweets
    from twx.client import TwitterApiClient

    transport = _make_transport(SAMPLE_TWEETS_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_user_tweets(
        client=client,
        username="karpathy",
        since="2026-04-14T00:00:00+00:00",
        until="2026-04-16T00:00:00+00:00",
        limit=5,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["query"]["since"] == "2026-04-14T00:00:00+00:00"
    assert output["query"]["until"] == "2026-04-16T00:00:00+00:00"
    assert output["query"]["limit"] == 5
