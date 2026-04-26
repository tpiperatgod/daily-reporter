"""Tests for the Twitter daily report skill scripts."""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FETCH_TWEETS = REPO_ROOT / ".claude" / "skills" / "twitter-daily-report" / "scripts" / "fetch_tweets.sh"


def test_fetch_tweets_derives_beijing_report_window_from_report_date(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls_dir = tmp_path / "calls"
    calls_dir.mkdir()
    fake_twx = bin_dir / "twx"
    fake_twx.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import os
            import sys
            from pathlib import Path

            args = sys.argv[1:]
            expected_since = os.environ["EXPECTED_SINCE"]
            expected_until = os.environ["EXPECTED_UNTIL"]
            if "--since" not in args or args[args.index("--since") + 1] != expected_since:
                print(f"bad since args: {args}", file=sys.stderr)
                raise SystemExit(17)
            if "--until" not in args or args[args.index("--until") + 1] != expected_until:
                print(f"bad until args: {args}", file=sys.stderr)
                raise SystemExit(18)

            username = args[args.index("--username") + 1]
            Path(os.environ["CALLS_DIR"], username).write_text(json.dumps(args))
            print(json.dumps({"ok": True, "data": {"tweets": []}, "query": {}, "meta": {}, "raw": None}))
            """
        ),
        encoding="utf-8",
    )
    fake_twx.chmod(0o755)

    out_dir = tmp_path / "twx_raw"
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "TWITTER_API_KEY": "test-key",
            "REPORT_DATE": "2026-04-25",
            "EXPECTED_SINCE": "2026-04-24T16:00:00+00:00",
            "EXPECTED_UNTIL": "2026-04-25T16:00:00+00:00",
            "CALLS_DIR": str(calls_dir),
        }
    )

    result = subprocess.run(
        ["bash", str(FETCH_TWEETS), str(out_dir)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert len(list(out_dir.glob("*.json"))) == 29
    assert len(list(calls_dir.iterdir())) == 29
