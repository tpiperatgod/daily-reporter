from __future__ import annotations

from pathlib import Path

from twx.client import TwitterApiClient
from twx.models import NormalizedTweet, SuccessEnvelope
from twx.state import load_state, save_state
from twx.transform import normalize_tweet


def rank_by_engagement(tweets: list[NormalizedTweet]) -> list[NormalizedTweet]:
    return sorted(
        tweets,
        key=lambda t: t.metrics.like_count + t.metrics.retweet_count + t.metrics.reply_count,
        reverse=True,
    )


def fetch_trending_tweets(
    *,
    client: TwitterApiClient,
    ranking: str = "upstream",
    limit: int = 20,
    include_raw: bool = False,
    state_path: Path | None = None,
) -> SuccessEnvelope:
    checkpoint = load_state(state_path) if state_path else {}

    raw_response = client.get_trending_tweets(
        query="trending",
        mode="top",
    )

    raw_data = raw_response.get("data", {})
    if isinstance(raw_data, list):
        raw_tweets = raw_data
    elif isinstance(raw_data, dict):
        raw_tweets = raw_data.get("tweets", [])
        if not isinstance(raw_tweets, list):
            raw_tweets = []
    else:
        raw_tweets = []

    # Search endpoint may also return tweets at top level
    if not raw_tweets and isinstance(raw_response.get("tweets"), list):
        raw_tweets = raw_response["tweets"]

    normalized = []
    for raw_tweet in raw_tweets:
        try:
            normalized.append(normalize_tweet(raw_tweet))
        except Exception:
            continue

    if ranking == "engagement":
        normalized = rank_by_engagement(normalized)

    normalized = normalized[:limit]
    tweets_data = [t.model_dump() for t in normalized]

    if state_path and normalized:
        highest_id = max(int(t.id) for t in normalized)
        save_state(state_path, {**checkpoint, "since_id": str(highest_id), "ranking": ranking})

    return SuccessEnvelope(
        data={"tweets": tweets_data},
        paging={"next_cursor": None, "has_more": False},
        query={
            "command": "trending",
            "ranking": ranking,
            "limit": limit,
        },
        meta={"count": len(tweets_data)},
        raw=raw_response if include_raw else None,
    )
