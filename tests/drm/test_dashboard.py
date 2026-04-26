"""Tests for dashboard model building."""

from __future__ import annotations

from pathlib import Path

from drm.dashboard import build_dashboard_model
from drm.reports import ReportRef


def test_dashboard_model_has_fixed_source_slots_and_missing_states(tmp_path: Path) -> None:
    tw = tmp_path / "tw-daily-2026-04-24.md"
    hn = tmp_path / "hn-daily-2026-04-25.md"
    tw.write_text(
        "# Tech Twitter 日报 — 2026-04-24\n\n## 今日头条\n\n### 1. A\n\nBody\n\n## 今日数据概览\n\n| 指标 | 数值 |\n|---|---:|\n| 当日总推文 | 1 |\n",
        encoding="utf-8",
    )
    hn.write_text(
        "# HN 高价值内容报告 — 2026-04-25\n\n## 今日判断\n\nBody\n\n## 精选条目\n\n### 1. B\n\nBody\n\n## 数据概览\n\n| 指标 | 数值 |\n|---|---:|\n| 最终入选 | 1 |\n",
        encoding="utf-8",
    )

    model = build_dashboard_model(
        [
            ReportRef(source="twitter", date="2026-04-24", path=tw),
            ReportRef(source="hackernews", date="2026-04-25", path=hn),
        ]
    )

    assert model.dates == ["2026-04-25", "2026-04-24"]
    assert model.reports_by_date["2026-04-25"]["hackernews"]["status"] == "available"
    assert model.reports_by_date["2026-04-25"]["twitter"]["status"] == "missing"
    assert model.reports_by_date["2026-04-25"]["producthunt"]["status"] == "missing"
    assert model.reports_by_date["2026-04-24"]["twitter"]["status"] == "available"


def test_search_index_uses_search_blocks(tmp_path: Path) -> None:
    report_path = tmp_path / "ph-daily-2026-04-24.md"
    report_path.write_text(
        "# Product Hunt Daily Scout - 2026-04-24\n\n## 今日判断\n\nBody\n\n## 深度精选\n\n### 1. MailCue - Email testing\n\nMailCue body\n\n## 数据概览\n\n| 指标 | 数值 |\n|---|---:|\n| Final picks | 1 |\n",
        encoding="utf-8",
    )

    model = build_dashboard_model([ReportRef(source="producthunt", date="2026-04-24", path=report_path)])

    headings = [entry["heading"] for entry in model.search_index]
    assert "深度精选" in headings
    assert "1. MailCue - Email testing" in headings
