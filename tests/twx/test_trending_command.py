"""Contract tests for the twx trending command."""

import json
from collections.abc import Mapping

import httpx


SAMPLE_TRENDING_PAYLOAD = {
    "data": [
        {
            "id": 300,
            "text": "Trending topic one",
            "url": "https://x.com/user1/status/300",
            "createdAt": "2026-04-15T16:00:00+00:00",
            "author": {"userName": "user1", "name": "User One"},
            "likes": 100,
            "retweets": 50,
            "replies": 20,
            "views": 5000,
        },
        {
            "id": 301,
            "text": "Trending topic two",
            "url": "https://x.com/user2/status/301",
            "createdAt": "2026-04-15T15:00:00+00:00",
            "author": {"userName": "user2", "name": "User Two"},
            "likes": 500,
            "retweets": 200,
            "replies": 80,
            "views": 20000,
        },
        {
            "id": 302,
            "text": "Trending topic three",
            "url": "https://x.com/user3/status/302",
            "createdAt": "2026-04-15T14:00:00+00:00",
            "author": {"userName": "user3", "name": "User Three"},
            "likes": 50,
            "retweets": 10,
            "replies": 5,
            "views": 1000,
        },
    ]
}


def _make_transport(payload: Mapping[str, object], status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return httpx.MockTransport(handler)


def test_trending_defaults_to_upstream_ranking():
    """twx trending defaults to upstream ranking mode."""
    from twx.client import TwitterApiClient
    from twx.commands.trending import fetch_trending_tweets

    transport = _make_transport(SAMPLE_TRENDING_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_trending_tweets(
        client=client,
        ranking="upstream",
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["ok"] is True
    assert output["query"]["command"] == "trending"
    assert output["query"]["ranking"] == "upstream"


def test_trending_engagement_ranking_resorts_candidate_set():
    """twx trending --ranking engagement sorts by total engagement."""
    from twx.client import TwitterApiClient
    from twx.commands.trending import fetch_trending_tweets

    transport = _make_transport(SAMPLE_TRENDING_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_trending_tweets(
        client=client,
        ranking="engagement",
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    tweets = output["data"]["tweets"]

    # Engagement = likes + retweets + replies
    # tweet 301: 500+200+80=780, tweet 300: 100+50+20=170, tweet 302: 50+10+5=65
    engagement_scores = [
        t["metrics"]["like_count"] + t["metrics"]["retweet_count"] + t["metrics"]["reply_count"] for t in tweets
    ]
    assert engagement_scores == sorted(engagement_scores, reverse=True)


def test_trending_respects_limit():
    """twx trending --limit caps the number of returned tweets."""
    from twx.client import TwitterApiClient
    from twx.commands.trending import fetch_trending_tweets

    transport = _make_transport(SAMPLE_TRENDING_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_trending_tweets(
        client=client,
        ranking="upstream",
        limit=2,
    )
    output = json.loads(envelope.model_dump_json())
    assert len(output["data"]["tweets"]) <= 2


def test_trending_with_raw_flag():
    """twx trending --raw includes the raw upstream payload."""
    from twx.client import TwitterApiClient
    from twx.commands.trending import fetch_trending_tweets

    transport = _make_transport(SAMPLE_TRENDING_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_trending_tweets(
        client=client,
        ranking="upstream",
        include_raw=True,
        limit=20,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["raw"] is not None


def test_trending_query_metadata():
    """Success envelope includes full query metadata."""
    from twx.client import TwitterApiClient
    from twx.commands.trending import fetch_trending_tweets

    transport = _make_transport(SAMPLE_TRENDING_PAYLOAD)
    client = TwitterApiClient(api_key="test", transport=transport)

    envelope = fetch_trending_tweets(
        client=client,
        ranking="engagement",
        limit=5,
    )
    output = json.loads(envelope.model_dump_json())
    assert output["query"]["command"] == "trending"
    assert output["query"]["ranking"] == "engagement"
    assert output["query"]["limit"] == 5
    assert output["meta"]["count"] == len(output["data"]["tweets"])


def test_rank_by_engagement_function():
    """Unit test for the engagement ranking helper."""
    from twx.commands.trending import rank_by_engagement
    from twx.models import NormalizedMetrics, NormalizedTweet

    tweets = [
        NormalizedTweet(
            id="1",
            text="low",
            url="https://x.com/a/1",
            author_username="a",
            created_at="2026-01-01T00:00:00+00:00",
            metrics=NormalizedMetrics(like_count=10, retweet_count=5, reply_count=2),
        ),
        NormalizedTweet(
            id="2",
            text="high",
            url="https://x.com/a/2",
            author_username="a",
            created_at="2026-01-01T00:00:00+00:00",
            metrics=NormalizedMetrics(like_count=100, retweet_count=50, reply_count=20),
        ),
        NormalizedTweet(
            id="3",
            text="mid",
            url="https://x.com/a/3",
            author_username="a",
            created_at="2026-01-01T00:00:00+00:00",
            metrics=NormalizedMetrics(like_count=50, retweet_count=25, reply_count=10),
        ),
    ]
    ranked = rank_by_engagement(tweets)
    assert ranked[0].id == "2"  # highest engagement
    assert ranked[1].id == "3"  # medium
    assert ranked[2].id == "1"  # lowest
