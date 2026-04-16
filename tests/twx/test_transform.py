"""Tests for tweet/user normalization transforms."""

import pytest

from twx.errors import TransformError
from twx.transform import (
    extract_media,
    extract_metrics,
    normalize_tweet,
    normalize_user,
)


# ---- Sample payloads ----

SAMPLE_TWEET = {
    "id": 1900000000000000000,
    "text": "Hello world! This is a test tweet.",
    "url": "https://x.com/karpathy/status/1900000000000000000",
    "createdAt": "2026-04-15T12:00:00+00:00",
    "author": {
        "userName": "karpathy",
        "name": "Andrej Karpathy",
    },
    "likes": 4200,
    "retweets": 800,
    "replies": 150,
    "views": 500000,
    "bookmarks": 200,
    "media": [
        {"type": "photo", "url": "https://pbs.twimg.com/img/test.jpg", "alt_text": "A test image"},
    ],
}


SAMPLE_TWEET_MINIMAL = {
    "id": 1900000000000000001,
    "text": "Just a tweet.",
    "author": {"userName": "testuser"},
}


def test_normalize_tweet_basic_fields():
    tweet = normalize_tweet(SAMPLE_TWEET)
    assert tweet.id == "1900000000000000000"
    assert tweet.text == "Hello world! This is a test tweet."
    assert tweet.url.startswith("https://x.com/")
    assert tweet.author_username == "karpathy"
    assert tweet.author_name == "Andrej Karpathy"
    assert tweet.created_at == "2026-04-15T12:00:00+00:00"


def test_normalize_tweet_metrics():
    tweet = normalize_tweet(SAMPLE_TWEET)
    assert tweet.metrics.like_count == 4200
    assert tweet.metrics.retweet_count == 800
    assert tweet.metrics.reply_count == 150
    assert tweet.metrics.view_count == 500000
    assert tweet.metrics.bookmark_count == 200


def test_normalize_tweet_media():
    tweet = normalize_tweet(SAMPLE_TWEET)
    assert len(tweet.media) == 1
    assert tweet.media[0].type == "photo"
    assert tweet.media[0].url == "https://pbs.twimg.com/img/test.jpg"


def test_normalize_tweet_flags_default_false():
    tweet = normalize_tweet(SAMPLE_TWEET)
    assert tweet.is_retweet is False
    assert tweet.is_reply is False
    assert tweet.is_quote is False


def test_normalize_tweet_retweet_flag():
    raw = {**SAMPLE_TWEET, "retweetedTweet": {"id": 123}}
    tweet = normalize_tweet(raw)
    assert tweet.is_retweet is True


def test_normalize_tweet_reply_flag():
    raw = {**SAMPLE_TWEET, "inReplyToStatus": {"id": 456}}
    tweet = normalize_tweet(raw)
    assert tweet.is_reply is True


def test_normalize_tweet_quote_flag():
    raw = {**SAMPLE_TWEET, "quoted_tweet": {"id": 789}}
    tweet = normalize_tweet(raw)
    assert tweet.is_quote is True


def test_normalize_tweet_minimal():
    """Minimal tweet with just id, text, and author."""
    tweet = normalize_tweet(SAMPLE_TWEET_MINIMAL)
    assert tweet.id == "1900000000000000001"
    assert tweet.text == "Just a tweet."
    assert tweet.author_username == "testuser"
    assert tweet.metrics.like_count == 0
    assert tweet.media == []


def test_normalize_tweet_url_generated():
    """URL is generated from author and id when not present."""
    raw = {"id": 123, "text": "test", "author": {"userName": "bob"}}
    tweet = normalize_tweet(raw)
    assert tweet.url == "https://x.com/bob/status/123"


def test_normalize_tweet_missing_text_raises():
    """Missing required 'text' field raises TransformError."""
    raw = {"id": 123, "author": {"userName": "bob"}}
    with pytest.raises(TransformError):
        normalize_tweet(raw)


def test_normalize_user():
    raw = {
        "userName": "karpathy",
        "name": "Andrej Karpathy",
        "bio": "AI researcher",
        "followersCount": 500000,
        "followingCount": 1000,
        "statusesCount": 10000,
    }
    user = normalize_user(raw)
    assert user.username == "karpathy"
    assert user.name == "Andrej Karpathy"
    assert user.bio == "AI researcher"
    assert user.followers_count == 500000
    assert user.following_count == 1000
    assert user.tweet_count == 10000


def test_normalize_user_minimal():
    raw = {"userName": "testuser"}
    user = normalize_user(raw)
    assert user.username == "testuser"
    assert user.name is None
    assert user.followers_count == 0


def test_extract_media_with_media_url_key():
    """Some payloads use media_url instead of url."""
    raw = {
        "media": [
            {"type": "photo", "media_url": "https://example.com/img.jpg"},
        ],
    }
    media = extract_media(raw)
    assert len(media) == 1
    assert media[0].url == "https://example.com/img.jpg"


def test_extract_metrics_defaults():
    """Missing metrics default to 0."""
    raw = {}
    metrics = extract_metrics(raw)
    assert metrics.like_count == 0
    assert metrics.retweet_count == 0
