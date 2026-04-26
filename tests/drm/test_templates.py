"""Tests for dashboard HTML rendering."""

from __future__ import annotations

import json
from pathlib import Path

from drm.dashboard import DashboardModel
from drm.dashboard_data import build_dashboard_model_from_data, load_dashboard_data
from drm.templates import render_dashboard_html, safe_json_for_script


def test_safe_json_for_script_escapes_script_breakouts() -> None:
    data = {"text": "</script><script>alert(1)</script>", "symbols": "<>&"}

    rendered = safe_json_for_script(data)

    assert "</script" not in rendered.lower()
    assert "<" not in rendered
    assert ">" not in rendered
    assert "&" not in rendered
    assert json.loads(rendered) == data


def test_render_dashboard_html_contains_app_shell_and_data() -> None:
    model = DashboardModel(
        dates=["2026-04-25"],
        reports_by_date={"2026-04-25": {}},
        search_index=[],
        generated_at="2026-04-25T00:00:00+00:00",
    )

    html = render_dashboard_html(model)

    assert "<!doctype html>" in html.lower()
    assert "Daily Report Manager" in html
    assert 'id="dashboard-data"' in html
    assert "Twitter" in html
    assert "Hacker News" in html
    assert "Product Hunt" in html
    assert "日报阅读工作台" in html
    assert "Signal List" in html
    assert "Detail Panel" in html


def test_render_dashboard_html_contains_selected_block_data() -> None:
    data = load_dashboard_data(Path("tests/drm/fixtures/dashboard-data-valid.json"))
    model = build_dashboard_model_from_data(data)

    html = render_dashboard_html(model)

    assert "selected_blocks" in html
    assert "target_block_id" in html
    assert "source_locator" in html
    assert "date_summaries" in html
    assert "hn-2026-04-25-deepseek-v4" in html
    assert "source_report_path" in html


def test_render_dashboard_html_uses_reading_workbench_actions() -> None:
    data = load_dashboard_data(Path("tests/drm/fixtures/dashboard-data-valid.json"))
    model = build_dashboard_model_from_data(data)

    html = render_dashboard_html(model)

    assert "Download Brief" in html
    assert "Original link" in html
    assert "rw-original-button" in html
    assert "buildBriefMarkdown" in html
    assert "downloadBrief" in html
    assert "sourcePath" in html
    assert "lineStart" in html


def test_render_dashboard_html_exposes_original_links_in_detail_panel() -> None:
    data = load_dashboard_data(Path("tests/drm/fixtures/dashboard-data-valid.json"))
    model = build_dashboard_model_from_data(data)

    html = render_dashboard_html(model)

    assert "Original link" in html
    assert "extractOriginalLinks" in html
    assert "originalLinks" in html
    assert "https://news.ycombinator.com/item?id=1" in html


def test_render_dashboard_html_gives_detail_panel_more_width_than_signal_list() -> None:
    data = load_dashboard_data(Path("tests/drm/fixtures/dashboard-data-valid.json"))
    model = build_dashboard_model_from_data(data)

    html = render_dashboard_html(model)

    assert "grid-template-columns: minmax(320px, .86fr) minmax(0, 1.34fr);" in html


def test_render_dashboard_html_removes_locator_debug_controls_from_detail_panel() -> None:
    data = load_dashboard_data(Path("tests/drm/fixtures/dashboard-data-valid.json"))
    model = build_dashboard_model_from_data(data)

    html = render_dashboard_html(model)

    assert "Source locator" not in html
    assert "Copy locator" not in html
    assert "Show source path" not in html


def test_render_dashboard_html_removes_nonfunctional_dashboard_affordances() -> None:
    data = load_dashboard_data(Path("tests/drm/fixtures/dashboard-data-valid.json"))
    model = build_dashboard_model_from_data(data)

    html = render_dashboard_html(model)

    assert "Export Brief" not in html
    assert "View Full Daily Report" not in html
    assert ">Open<" not in html
