#!/usr/bin/env python3
"""Inventory daily report Markdown files for daily-report-manager."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from drm.anchors import make_unique_anchor, normalize_heading
from drm.parser import HEADING_RE
from drm.reports import discover_reports


def inventory_report(path: Path, *, source: str, date: str) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = ""
    headings: list[dict] = []
    used: set[str] = set()
    for index, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group("marks"))
        heading = normalize_heading(match.group("heading"))
        if level == 1 and not title:
            title = heading
            continue
        if level in (2, 3):
            headings.append(
                {
                    "level": level,
                    "heading": heading,
                    "line_start": index,
                    "anchor": make_unique_anchor(heading, used),
                }
            )
    return {
        "source": source,
        "date": date,
        "path": path.as_posix(),
        "title": title,
        "headings": headings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=Path("docs/reports"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        refs = discover_reports(args.reports_dir)
        reports = [inventory_report(ref.path, source=ref.source, date=ref.date) for ref in refs]
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    dates = sorted({report["date"] for report in reports}, reverse=True)
    doc = {"reports_dir": args.reports_dir.as_posix(), "dates": dates, "reports": reports}
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
