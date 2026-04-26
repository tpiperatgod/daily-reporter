"""Tests for the Hacker News daily report skill scripts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
FETCH_POOL = REPO_ROOT / ".claude" / "skills" / "hn-daily-report" / "scripts" / "fetch_pool.sh"


@pytest.fixture(autouse=True)
def require_jq():
    if shutil.which("jq") is None:
        pytest.skip("jq is required for hn-daily-report script tests")


def test_fetch_pool_filters_candidates_to_beijing_report_date(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_hnx = bin_dir / "hnx"
    fake_hnx.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import sys

            source = sys.argv[1]
            rows = {
                "top": [
                    {"id": 1, "type": "story", "title": "before", "created_at": "2026-04-24T15:59:59+00:00"},
                    {"id": 2, "type": "story", "title": "inside top", "created_at": "2026-04-24T16:00:00+00:00"},
                ],
                "best": [
                    {"id": 2, "type": "story", "title": "duplicate", "created_at": "2026-04-24T16:00:00+00:00"},
                    {"id": 3, "type": "story", "title": "inside best", "created_at": "2026-04-25T15:59:59+00:00"},
                ],
                "new": [
                    {"id": 4, "type": "story", "title": "after", "created_at": "2026-04-25T16:00:00+00:00"},
                ],
            }[source]
            print(json.dumps({"ok": True, "data": rows, "query": {"source": source}, "meta": {}, "raw": None}))
            """
        ),
        encoding="utf-8",
    )
    fake_hnx.chmod(0o755)

    output = tmp_path / "pool.json"
    tmp_dir = tmp_path / "tmp"
    tmp_dir.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "REPORT_DATE": "2026-04-25",
            "TMP_DIR": str(tmp_dir),
        }
    )

    result = subprocess.run(
        ["bash", str(FETCH_POOL), str(output)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    doc = json.loads(output.read_text())
    assert [item["id"] for item in doc["data"]] == [2, 3]
    assert doc["query"]["report_date"] == "2026-04-25"
    assert doc["query"]["report_timezone"] == "Asia/Shanghai"
    assert doc["query"]["window"]["since_utc"] == "2026-04-24T16:00:00+00:00"
    assert doc["query"]["window"]["until_utc"] == "2026-04-25T16:00:00+00:00"
    assert doc["meta"]["candidate_count_before_date_filter"] == 4
    assert doc["meta"]["filtered_by_report_window"] == 2
