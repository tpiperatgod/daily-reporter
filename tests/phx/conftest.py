"""Shared fixtures for phx tests."""

from __future__ import annotations

import copy

import pytest


@pytest.fixture
def sample_post() -> dict:
    return {
        "id": "123456",
        "slug": "sample-launch",
        "name": "Sample Launch",
        "tagline": "Ship better agent workflows",
        "description": "A focused test payload for Product Hunt posts.",
        "url": "https://www.producthunt.com/posts/sample-launch",
        "website": "https://example.com",
        "votesCount": 321,
        "commentsCount": 12,
        "dailyRank": 3,
        "weeklyRank": 20,
        "monthlyRank": 80,
        "yearlyRank": None,
        "reviewsCount": 2,
        "reviewsRating": 4.5,
        "createdAt": "2026-04-24T08:00:00Z",
        "featuredAt": "2026-04-24T09:00:00Z",
        "thumbnail": {"type": "image", "url": "https://example.com/thumb.png", "videoUrl": None},
        "makers": [
            {
                "id": "maker-1",
                "name": "Jane Maker",
                "username": "jane",
                "url": "https://www.producthunt.com/@jane",
                "twitterUsername": "jane_x",
                "headline": "Builder",
                "websiteUrl": "https://jane.example",
            }
        ],
        "topics": {
            "nodes": [
                {
                    "id": "topic-1",
                    "name": "Artificial Intelligence",
                    "slug": "artificial-intelligence",
                    "url": "https://www.producthunt.com/topics/artificial-intelligence",
                }
            ]
        },
        "media": [{"type": "image", "url": "https://example.com/media.png", "videoUrl": None}],
        "productLinks": [{"type": "Website", "url": "https://example.com"}],
    }


@pytest.fixture
def sample_post_factory(sample_post):
    def _factory(**overrides):
        payload = copy.deepcopy(sample_post)
        payload.update(overrides)
        return payload

    return _factory
