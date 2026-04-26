"""Tests for curated dashboard data validation and model conversion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from drm.anchors import make_unique_anchor, normalize_heading, slugify
from drm.dashboard_data import build_dashboard_model_from_data, load_dashboard_data, validate_dashboard_data
from drm.errors import InputError


FIXTURE = Path("tests/drm/fixtures/dashboard-data-valid.json")


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_slugify_matches_dashboard_locator_contract() -> None:
    assert normalize_heading("📰 今日头条") == "今日头条"
    assert slugify("1. DeepSeek V4 开源：benchmarks 不等于体验") == "1-deepseek-v4-开源-benchmarks-不等于体验"


def test_make_unique_anchor_suffixes_duplicates() -> None:
    used: set[str] = set()

    assert make_unique_anchor("精选条目", used) == "精选条目"
    assert make_unique_anchor("精选条目", used) == "精选条目-2"


def test_valid_dashboard_data_builds_model() -> None:
    data = load_fixture()

    model = build_dashboard_model_from_data(data)

    assert model.dates == ["2026-04-25"]
    assert model.date_summaries["2026-04-25"] == "Today centers on model choice and toolchain trust."
    report = model.reports_by_date["2026-04-25"]["hackernews"]
    assert report["selected_blocks"][0]["html"]
    assert "<strong>curated</strong>" in report["selected_blocks"][0]["html"]
    assert report["selected_blocks"][0]["original_links"] == [
        {"label": "source", "url": "https://news.ycombinator.com/item?id=1"}
    ]
    assert model.search_index[0]["target_block_id"] == "hn-2026-04-25-deepseek-v4"


def test_original_link_from_source_report_prefers_matching_tweet_metrics(tmp_path: Path) -> None:
    data = load_fixture()
    report_path = tmp_path / "tw.md"
    report_path.write_text(
        """### @example

**First**
> — ♥ 1 🔁 2 💬 3 | [原文](https://x.com/example/status/1)

**Second**
> — ♥ 4 🔁 5 💬 6 | [原文](https://x.com/example/status/2)
""",
        encoding="utf-8",
    )
    report = data["dates"][0]["reports"]["hackernews"]
    block = report["selected_blocks"][0]
    path = str(report_path)
    report["source_report_path"] = path
    report["source_locator"]["path"] = path
    report["source_locator"]["line_start"] = 1
    block["source_report_path"] = path
    block["source_locator"]["path"] = path
    block["source_locator"]["line_start"] = 1
    block["excerpt_markdown"] = "The matching tweet.\n\n— @example ♥ 4 🔁 5 💬 6"
    data["search_index"][0]["source_report_path"] = path
    data["search_index"][0]["source_locator"]["path"] = path

    model = build_dashboard_model_from_data(data)

    links = model.reports_by_date["2026-04-25"]["hackernews"]["selected_blocks"][0]["original_links"]
    assert links == [{"label": "原文", "url": "https://x.com/example/status/2"}]


def test_missing_schema_version_fails() -> None:
    data = load_fixture()
    data.pop("schema_version")

    with pytest.raises(InputError, match="schema_version"):
        validate_dashboard_data(data)


def test_search_target_must_exist() -> None:
    data = load_fixture()
    data["search_index"][0]["target_block_id"] = "missing-block"

    with pytest.raises(InputError, match="target_block_id"):
        validate_dashboard_data(data)


def test_available_report_requires_zero_block_reason() -> None:
    data = load_fixture()
    report = data["dates"][0]["reports"]["hackernews"]
    report["selected_blocks"] = []

    with pytest.raises(InputError, match="x_reason_no_blocks"):
        validate_dashboard_data(data)


def test_oversized_excerpt_fails() -> None:
    data = load_fixture()
    block = data["dates"][0]["reports"]["hackernews"]["selected_blocks"][0]
    block["excerpt_markdown"] = "x" * 801

    with pytest.raises(InputError, match="excerpt_markdown"):
        validate_dashboard_data(data)


def test_load_dashboard_data_missing_input() -> None:
    with pytest.raises(InputError, match="dashboard data input does not exist"):
        load_dashboard_data(Path("/nonexistent/path.json"))
