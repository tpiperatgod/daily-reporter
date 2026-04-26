"""Tests for daily-report-manager skill helper scripts."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "daily-report-manager"
INVENTORY = SKILL_DIR / "scripts" / "inventory_reports.py"
VALIDATE = SKILL_DIR / "scripts" / "validate_dashboard_data.py"


def run_python(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_inventory_reports_emits_dates_reports_and_heading_lines(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "hn-daily-2026-04-25.md").write_text(
        textwrap.dedent(
            """\
            # HN 高价值内容报告 — 2026-04-25

            ## 今日判断

            Body

            ## 精选条目

            ### 1. DeepSeek V4

            Body
            """
        ),
        encoding="utf-8",
    )
    output = tmp_path / "inventory.json"

    result = run_python(INVENTORY, "--reports-dir", str(reports_dir), "--output", str(output))

    assert result.returncode == 0, result.stderr
    doc = json.loads(output.read_text(encoding="utf-8"))
    assert doc["dates"] == ["2026-04-25"]
    assert doc["reports"][0]["source"] == "hackernews"
    assert doc["reports"][0]["title"] == "HN 高价值内容报告 — 2026-04-25"
    assert doc["reports"][0]["headings"][0]["heading"] == "今日判断"
    assert doc["reports"][0]["headings"][0]["line_start"] == 3


def test_validate_dashboard_data_script_accepts_valid_data(tmp_path: Path) -> None:
    data = tmp_path / "dashboard-data.json"
    data.write_text(
        Path("tests/drm/fixtures/dashboard-data-valid.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = run_python(VALIDATE, str(data))

    assert result.returncode == 0, result.stderr
    assert "valid dashboard data" in result.stdout


def test_validate_dashboard_data_script_rejects_missing_target(tmp_path: Path) -> None:
    doc = json.loads(Path("tests/drm/fixtures/dashboard-data-valid.json").read_text(encoding="utf-8"))
    doc["search_index"][0]["target_block_id"] = "missing"
    data = tmp_path / "dashboard-data.json"
    data.write_text(json.dumps(doc), encoding="utf-8")

    result = run_python(VALIDATE, str(data))

    assert result.returncode == 2
    assert "target_block_id" in result.stderr


def test_validate_dashboard_data_script_rejects_locator_missing_from_inventory(tmp_path: Path) -> None:
    data = tmp_path / "dashboard-data.json"
    data.write_text(
        Path("tests/drm/fixtures/dashboard-data-valid.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps({"reports_dir": "docs/reports", "dates": [], "reports": []}),
        encoding="utf-8",
    )

    result = run_python(VALIDATE, str(data), "--inventory", str(inventory))

    assert result.returncode == 2
    assert "inventory" in result.stderr


def test_daily_report_manager_skill_files_exist() -> None:
    skill = SKILL_DIR / "SKILL.md"
    schema = SKILL_DIR / "references" / "dashboard-schema.md"

    assert skill.exists()
    assert schema.exists()
    text = skill.read_text(encoding="utf-8")
    assert "daily report manager" in text.lower()
    assert "dashboard-data.json" in text
    assert "validate_dashboard_data.py" in text
