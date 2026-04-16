from __future__ import annotations

from pathlib import Path

from twx.client import TwitterApiClient
from twx.models import SuccessEnvelope
from twx.state import load_state, save_state
from twx.transform import normalize_tweet


def fetch_user_tweets(
    *,
    client: TwitterApiClient,
    username: str,
    since: str | None = None,
    until: str | None = None,
    limit: int = 20,
    include_replies: bool = False,
    include_raw: bool = False,
    state_path: Path | None = None,
) -> SuccessEnvelope:
    checkpoint = load_state(state_path) if state_path else {}

    raw_response = client.get_user_tweets(
        username=username,
        cursor=None,
        include_replies=include_replies,
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

    normalized = []
    for raw_tweet in raw_tweets:
        try:
            normalized.append(normalize_tweet(raw_tweet))
        except Exception:
            continue

    if since is not None:
        normalized = [t for t in normalized if t.created_at >= since]
    if until is not None:
        normalized = [t for t in normalized if t.created_at <= until]

    normalized = normalized[:limit]
    tweets_data = [t.model_dump() for t in normalized]

    if state_path and normalized:
        highest_id = max(int(t.id) for t in normalized)
        save_state(state_path, {**checkpoint, "since_id": str(highest_id), "last_username": username})

    return SuccessEnvelope(
        data={"tweets": tweets_data},
        paging={"next_cursor": None, "has_more": False},
        query={
            "command": "user",
            "username": username,
            "since": since,
            "until": until,
            "limit": limit,
        },
        meta={"count": len(tweets_data)},
        raw=raw_response if include_raw else None,
    )
