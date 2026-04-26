"""Report discovery for drm."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from drm.errors import InputError

REPORT_RE = re.compile(r"^(?P<prefix>tw|hn|ph)-daily-(?P<date>\d{4}-\d{2}-\d{2})\.md$")

SOURCE_BY_PREFIX = {
    "tw": "twitter",
    "hn": "hackernews",
    "ph": "producthunt",
}

SOURCE_ORDER = ("twitter", "hackernews", "producthunt")


@dataclass(frozen=True)
class ReportRef:
    source: str
    date: str
    path: Path


def parse_report_filename(path: Path) -> tuple[str, str] | None:
    match = REPORT_RE.match(path.name)
    if not match:
        return None
    return SOURCE_BY_PREFIX[match.group("prefix")], match.group("date")


def _date_key(date: str) -> int:
    return int(date.replace("-", ""))


def discover_reports(reports_dir: Path) -> list[ReportRef]:
    if not reports_dir.exists() or not reports_dir.is_dir():
        raise InputError(f"reports directory does not exist: {reports_dir}")

    reports: list[ReportRef] = []
    for path in reports_dir.iterdir():
        parsed = parse_report_filename(path)
        if parsed is None:
            continue
        source, date = parsed
        reports.append(ReportRef(source=source, date=date, path=path))

    if not reports:
        raise InputError(f"no daily reports found in {reports_dir}")

    source_rank = {source: index for index, source in enumerate(SOURCE_ORDER)}
    return sorted(
        reports,
        key=lambda report: (-_date_key(report.date), source_rank[report.source], report.path.name),
    )
