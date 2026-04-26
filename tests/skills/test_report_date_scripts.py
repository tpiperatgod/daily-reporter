"""Tests for shared daily report date/window helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_resolver(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", "-m", "drm.report_window", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_default_report_date_is_beijing_yesterday() -> None:
    result = run_resolver("--now", "2026-04-26T09:30:00+08:00")

    assert result.returncode == 0, result.stderr
    doc = json.loads(result.stdout)
    assert doc["report_date"] == "2026-04-25"
    assert doc["report_timezone"] == "Asia/Shanghai"
    assert doc["date_source"] == "default_yesterday"
    assert doc["since_utc"] == "2026-04-24T16:00:00+00:00"
    assert doc["until_utc"] == "2026-04-25T16:00:00+00:00"
    assert doc["since_local"] == "2026-04-25T00:00:00+08:00"
    assert doc["until_local"] == "2026-04-26T00:00:00+08:00"


def test_explicit_report_date_keeps_beijing_window() -> None:
    result = run_resolver("--date", "2026-04-25")

    assert result.returncode == 0, result.stderr
    doc = json.loads(result.stdout)
    assert doc["report_date"] == "2026-04-25"
    assert doc["date_source"] == "explicit"
    assert doc["since_utc"] == "2026-04-24T16:00:00+00:00"
    assert doc["until_utc"] == "2026-04-25T16:00:00+00:00"
