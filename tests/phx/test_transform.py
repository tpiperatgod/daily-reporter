"""Tests for Product Hunt post normalization."""

from __future__ import annotations

import pytest

from phx.errors import TransformError
from phx.transform import normalize_launch, normalize_product_detail


def test_normalize_launch_maps_core_fields(sample_post):
    launch = normalize_launch(sample_post)

    assert launch.type == "launch"
    assert launch.id == "123456"
    assert launch.slug == "sample-launch"
    assert launch.product_hunt_url == "https://www.producthunt.com/posts/sample-launch"
    assert launch.website_url == "https://example.com"
    assert launch.thumbnail_url == "https://example.com/thumb.png"
    assert launch.votes_count == 321
    assert launch.comments_count == 12
    assert launch.ranking == 3
    assert launch.featured is True
    assert launch.topics == ["Artificial Intelligence"]
    assert launch.makers == ["jane"]


def test_normalize_launch_uses_maker_name_when_username_missing(sample_post_factory):
    raw = sample_post_factory(makers=[{"id": "maker-1", "name": "Jane Maker", "username": None}])

    launch = normalize_launch(raw)

    assert launch.makers == ["Jane Maker"]


def test_normalize_launch_optional_nested_fields(sample_post_factory):
    raw = sample_post_factory(thumbnail=None, makers=None, topics=None, featuredAt=None)

    launch = normalize_launch(raw)

    assert launch.thumbnail_url is None
    assert launch.makers == []
    assert launch.topics == []
    assert launch.featured is False


def test_normalize_launch_missing_required_field_raises(sample_post_factory):
    raw = sample_post_factory()
    raw.pop("id")

    with pytest.raises(TransformError, match="id"):
        normalize_launch(raw)


def test_normalize_product_detail_maps_extended_fields(sample_post):
    detail = normalize_product_detail(sample_post)

    assert detail.type == "product"
    assert detail.reviews_count == 2
    assert detail.reviews_rating == 4.5
    assert detail.weekly_rank == 20
    assert detail.media[0].url == "https://example.com/media.png"
    assert detail.product_links[0].url == "https://example.com"
    assert detail.topics[0].slug == "artificial-intelligence"
    assert detail.makers[0].twitter_username == "jane_x"
