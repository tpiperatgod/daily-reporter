"""Tests for phx.commands.launches.fetch_launches."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from phx.commands.launches import build_launch_window, fetch_launches
from phx.errors import InvalidInputError


class FakeProductHuntClient:
    def __init__(self, *, data=None, raw=None):
        self.data = data or {"posts": {"nodes": [], "pageInfo": {}, "totalCount": 0}}
        self.raw = raw
        self.calls = []

    async def fetch_launches(self, **kwargs):
        self.calls.append(kwargs)
        return self.data, self.raw if kwargs.get("include_raw") else None


def test_build_window_from_explicit_date():
    window = build_launch_window(date="2026-04-24", after=None, before=None)

    assert window.date == "2026-04-24"
    assert window.date_source == "explicit"
    assert window.after == "2026-04-24T00:00:00-07:00"
    assert window.before == "2026-04-25T00:00:00-07:00"


def test_build_window_defaults_to_current_product_hunt_day():
    now = datetime(2026, 4, 24, 18, 30, tzinfo=ZoneInfo("America/Los_Angeles"))

    window = build_launch_window(date=None, after=None, before=None, now=now)

    assert window.date == "2026-04-24"
    assert window.date_source == "default"


def test_build_window_rejects_mixed_date_and_window():
    with pytest.raises(InvalidInputError):
        build_launch_window(date="2026-04-24", after="2026-04-24T00:00:00-07:00", before="2026-04-25T00:00:00-07:00")


def test_build_window_rejects_partial_window():
    with pytest.raises(InvalidInputError):
        build_launch_window(date=None, after="2026-04-24T00:00:00-07:00", before=None)


def test_build_window_rejects_naive_datetime():
    with pytest.raises(InvalidInputError):
        build_launch_window(date=None, after="2026-04-24T00:00:00", before="2026-04-25T00:00:00-07:00")


@pytest.mark.asyncio
async def test_fetch_launches_success(sample_post):
    data = {"posts": {"nodes": [sample_post], "pageInfo": {"hasNextPage": False, "endCursor": None}, "totalCount": 1}}
    client = FakeProductHuntClient(data=data)

    envelope = await fetch_launches(client=client, date="2026-04-24", limit=20)

    assert envelope.ok is True
    assert envelope.data[0]["slug"] == "sample-launch"
    assert envelope.query["date_source"] == "explicit"
    assert envelope.meta["returned"] == 1
    assert envelope.meta["total_count"] == 1
    assert envelope.raw is None
    assert client.calls[0]["limit"] == 20


@pytest.mark.asyncio
async def test_fetch_launches_include_raw(sample_post):
    raw = {"data": {"posts": {"nodes": [sample_post]}}}
    data = {"posts": {"nodes": [sample_post], "pageInfo": {}, "totalCount": 1}}
    client = FakeProductHuntClient(data=data, raw=raw)

    envelope = await fetch_launches(client=client, date="2026-04-24", limit=20, include_raw=True)

    assert envelope.raw == raw


@pytest.mark.asyncio
async def test_fetch_launches_counts_transform_errors(sample_post):
    bad = dict(sample_post)
    bad.pop("id")
    data = {"posts": {"nodes": [sample_post, bad], "pageInfo": {}, "totalCount": 2}}
    client = FakeProductHuntClient(data=data)

    envelope = await fetch_launches(client=client, date="2026-04-24", limit=20)

    assert len(envelope.data) == 1
    assert envelope.meta["transform_errors"] == 1
