"""Tests for phx Pydantic models."""

from __future__ import annotations

import json

from phx.models import MakerRef, MediaRef, NormalizedLaunch, ProductDetail, ProductLinkRef, SuccessEnvelope, TopicRef


def test_normalized_launch_round_trip():
    launch = NormalizedLaunch(
        id="123",
        slug="sample",
        name="Sample",
        tagline="Launch tagline",
        description="Description",
        product_hunt_url="https://www.producthunt.com/posts/sample",
        website_url="https://example.com",
        thumbnail_url="https://example.com/thumb.png",
        votes_count=10,
        comments_count=2,
        topics=["AI"],
        makers=["jane"],
        created_at="2026-04-24T08:00:00Z",
        featured_at="2026-04-24T09:00:00Z",
        ranking=1,
        featured=True,
    )

    payload = launch.model_dump()

    assert payload["type"] == "launch"
    assert payload["votes_count"] == 10


def test_product_detail_nested_refs_round_trip():
    detail = ProductDetail(
        id="123",
        slug="sample",
        name="Sample",
        tagline=None,
        description=None,
        product_hunt_url="https://www.producthunt.com/posts/sample",
        website_url=None,
        thumbnail_url=None,
        votes_count=10,
        comments_count=2,
        topics=[TopicRef(id="topic-1", name="AI", slug="ai", url=None)],
        makers=[MakerRef(id="maker-1", name="Jane", username="jane")],
        media=[MediaRef(type="image", url="https://example.com/media.png")],
        product_links=[ProductLinkRef(type="Website", url="https://example.com")],
        created_at=None,
        featured_at=None,
        ranking=None,
        featured=False,
    )

    payload = detail.model_dump()

    assert payload["type"] == "product"
    assert payload["topics"][0]["slug"] == "ai"
    assert payload["makers"][0]["username"] == "jane"


def test_success_envelope_serializes():
    envelope = SuccessEnvelope(data=[], query={"command": "launches"}, meta={"returned": 0}, raw=None)

    payload = json.loads(envelope.model_dump_json())

    assert payload == {
        "ok": True,
        "data": [],
        "query": {"command": "launches"},
        "meta": {"returned": 0},
        "raw": None,
    }
