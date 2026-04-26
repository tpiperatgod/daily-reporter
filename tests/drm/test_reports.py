"""Tests for daily report discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from drm.errors import DRMError
from drm.reports import ReportRef, discover_reports, parse_report_filename


def test_parse_report_filename_recognizes_sources() -> None:
    assert parse_report_filename(Path("tw-daily-2026-04-24.md")) == ("twitter", "2026-04-24")
    assert parse_report_filename(Path("hn-daily-2026-04-25.md")) == ("hackernews", "2026-04-25")
    assert parse_report_filename(Path("ph-daily-2026-04-24.md")) == ("producthunt", "2026-04-24")


def test_parse_report_filename_ignores_unrelated_files() -> None:
    assert parse_report_filename(Path("README.md")) is None
    assert parse_report_filename(Path("tw-daily-not-a-date.md")) is None
    assert parse_report_filename(Path("daily-2026-04-24.md")) is None


def test_discover_reports_returns_sorted_refs(tmp_path: Path) -> None:
    for name in [
        "hn-daily-2026-04-25.md",
        "tw-daily-2026-04-24.md",
        "notes.md",
        "ph-daily-2026-04-24.md",
    ]:
        (tmp_path / name).write_text("# report\n", encoding="utf-8")

    reports = discover_reports(tmp_path)

    assert reports == [
        ReportRef(source="hackernews", date="2026-04-25", path=tmp_path / "hn-daily-2026-04-25.md"),
        ReportRef(source="twitter", date="2026-04-24", path=tmp_path / "tw-daily-2026-04-24.md"),
        ReportRef(source="producthunt", date="2026-04-24", path=tmp_path / "ph-daily-2026-04-24.md"),
    ]


def test_discover_reports_errors_when_directory_missing(tmp_path: Path) -> None:
    with pytest.raises(DRMError) as exc:
        discover_reports(tmp_path / "missing")

    assert exc.value.exit_code == 2


def test_discover_reports_errors_when_no_reports(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# nope\n", encoding="utf-8")

    with pytest.raises(DRMError) as exc:
        discover_reports(tmp_path)

    assert exc.value.exit_code == 2
