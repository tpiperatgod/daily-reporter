"""Tests for phx.commands.product.fetch_product."""

from __future__ import annotations

import pytest

from phx.commands.product import classify_product_ref, fetch_product
from phx.errors import InvalidInputError, NotFoundError


class FakeProductHuntClient:
    def __init__(self, *, post=None, raw=None):
        self.post = post
        self.raw = raw
        self.calls = []

    async def fetch_product(self, **kwargs):
        self.calls.append(kwargs)
        return self.post, self.raw if kwargs.get("include_raw") else None


def test_classify_product_ref_auto_id():
    assert classify_product_ref("123456") == ("id", "auto")


def test_classify_product_ref_auto_slug():
    assert classify_product_ref("cursor") == ("slug", "auto")


def test_classify_product_ref_force_id():
    assert classify_product_ref("opaque-id", force_id=True) == ("id", "explicit")


def test_classify_product_ref_force_slug():
    assert classify_product_ref("123456", force_slug=True) == ("slug", "explicit")


def test_classify_product_ref_rejects_conflicting_flags():
    with pytest.raises(InvalidInputError):
        classify_product_ref("123456", force_id=True, force_slug=True)


@pytest.mark.asyncio
async def test_fetch_product_success(sample_post):
    client = FakeProductHuntClient(post=sample_post)

    envelope = await fetch_product(client=client, ref="sample-launch")

    assert envelope.ok is True
    assert envelope.data["type"] == "product"
    assert envelope.query["ref_type"] == "slug"
    assert envelope.query["ref_source"] == "auto"
    assert envelope.meta["returned"] == 1
    assert client.calls[0]["ref_type"] == "slug"


@pytest.mark.asyncio
async def test_fetch_product_explicit_id(sample_post):
    client = FakeProductHuntClient(post=sample_post)

    envelope = await fetch_product(client=client, ref="opaque-id", force_id=True)

    assert envelope.query["ref_type"] == "id"
    assert envelope.query["ref_source"] == "explicit"
    assert client.calls[0]["ref_type"] == "id"


@pytest.mark.asyncio
async def test_fetch_product_not_found():
    client = FakeProductHuntClient(post=None)

    with pytest.raises(NotFoundError, match="missing"):
        await fetch_product(client=client, ref="missing")


@pytest.mark.asyncio
async def test_fetch_product_include_raw(sample_post):
    raw = {"data": {"post": sample_post}}
    client = FakeProductHuntClient(post=sample_post, raw=raw)

    envelope = await fetch_product(client=client, ref="sample-launch", include_raw=True)

    assert envelope.raw == raw
