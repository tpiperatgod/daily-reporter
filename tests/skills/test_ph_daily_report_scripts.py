"""Tests for the Product Hunt daily report skill scripts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "ph-daily-report"
FETCH_LAUNCHES = SKILL_DIR / "scripts" / "fetch_launches.sh"
FETCH_DETAILS = SKILL_DIR / "scripts" / "fetch_details.sh"


@pytest.fixture(autouse=True)
def require_jq():
    if shutil.which("jq") is None:
        pytest.skip("jq is required for ph-daily-report script tests")


@pytest.fixture
def fake_path(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    phx = bin_dir / "phx"
    phx.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import sys

            launches = [
                {
                    "type": "launch",
                    "id": "1",
                    "slug": "agent-workbench",
                    "name": "Agent Workbench",
                    "tagline": "Build AI workflows faster",
                    "description": "A builder for agent workflows.",
                    "product_hunt_url": "https://www.producthunt.com/posts/agent-workbench",
                    "website_url": "https://agent.example",
                    "thumbnail_url": None,
                    "votes_count": 120,
                    "comments_count": 18,
                    "topics": ["Artificial Intelligence", "Developer Tools"],
                    "makers": ["alice"],
                    "created_at": "2026-04-24T08:00:00Z",
                    "featured_at": "2026-04-24T08:30:00Z",
                    "ranking": 1,
                    "featured": True
                },
                {
                    "type": "launch",
                    "id": "2",
                    "slug": "sales-glitter",
                    "name": "Sales Glitter",
                    "tagline": "AI sales sparkle",
                    "description": "A sales assistant.",
                    "product_hunt_url": "https://www.producthunt.com/posts/sales-glitter",
                    "website_url": "https://sales.example",
                    "thumbnail_url": None,
                    "votes_count": 90,
                    "comments_count": 5,
                    "topics": ["Sales", "Artificial Intelligence"],
                    "makers": ["bob"],
                    "created_at": "2026-04-24T09:00:00Z",
                    "featured_at": "2026-04-24T09:30:00Z",
                    "ranking": 2,
                    "featured": True
                }
            ]

            products = {
                "agent-workbench": {
                    **launches[0],
                    "type": "product",
                    "reviews_count": 4,
                    "reviews_rating": 4.8,
                    "topics": [
                        {
                            "id": "t1",
                            "name": "Artificial Intelligence",
                            "slug": "artificial-intelligence",
                            "url": "https://www.producthunt.com/topics/artificial-intelligence"
                        }
                    ],
                    "makers": [
                        {
                            "id": "m1",
                            "name": "Alice",
                            "username": "alice",
                            "url": "https://www.producthunt.com/@alice",
                            "twitter_username": "alice",
                            "headline": "Builder",
                            "website_url": "https://alice.example"
                        }
                    ],
                    "media": [
                        {"type": "image", "url": "https://cdn.example/image.png", "video_url": None}
                    ],
                    "product_links": [
                        {"type": "Website", "url": "https://agent.example"}
                    ],
                    "weekly_rank": 3,
                    "monthly_rank": None,
                    "yearly_rank": None
                }
            }

            if len(sys.argv) >= 2 and sys.argv[1] == "launches":
                print(json.dumps({
                    "ok": True,
                    "data": launches,
                    "query": {
                        "command": "launches",
                        "date": "2026-04-24",
                        "date_source": "default",
                        "after": "2026-04-24T00:00:00-07:00",
                        "before": "2026-04-25T00:00:00-07:00",
                        "timezone": "America/Los_Angeles",
                        "limit": 30,
                        "featured": True,
                        "order": "RANKING",
                        "raw": False
                    },
                    "meta": {"returned": len(launches), "limit": 30},
                    "raw": None
                }))
                raise SystemExit(0)

            if len(sys.argv) >= 3 and sys.argv[1] == "product":
                slug = sys.argv[2]
                if slug in products:
                    print(json.dumps({
                        "ok": True,
                        "data": products[slug],
                        "query": {"command": "product", "ref": slug, "ref_type": "slug", "ref_source": "auto", "raw": False},
                        "meta": {"returned": 1},
                        "raw": None
                    }))
                    raise SystemExit(0)
                print(json.dumps({"ok": False, "error": {"type": "not_found", "message": f"missing {slug}", "details": {}}}), file=sys.stderr)
                raise SystemExit(5)

            print(f"unexpected phx args: {sys.argv[1:]}", file=sys.stderr)
            raise SystemExit(99)
            """
        )
    )
    phx.chmod(0o755)
    return bin_dir


def run_script(
    script: Path, *args: str, fake_path: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env["PATH"] = f"{fake_path}{os.pathsep}{merged_env['PATH']}"
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=REPO_ROOT,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_fetch_launches_emits_launch_pool(tmp_path: Path, fake_path: Path):
    output = tmp_path / "launches.json"

    result = run_script(FETCH_LAUNCHES, str(output), fake_path=fake_path)

    assert result.returncode == 0, result.stderr
    doc = json.loads(output.read_text())
    assert doc["ok"] is True
    assert doc["data"]["launches"][0]["slug"] == "agent-workbench"
    assert doc["query"]["command"] == "ph-daily-report/fetch_launches"
    assert doc["query"]["resolved_date"] == "2026-04-24"
    assert doc["meta"]["launch_count"] == 2


def test_fetch_details_merges_success_and_failure(tmp_path: Path, fake_path: Path):
    launches = tmp_path / "launches.json"
    pool = tmp_path / "pool.json"
    slugs = tmp_path / "slugs.txt"
    slugs.write_text("agent-workbench\nsales-glitter\n")

    first = run_script(FETCH_LAUNCHES, str(launches), fake_path=fake_path)
    assert first.returncode == 0, first.stderr

    result = run_script(
        FETCH_DETAILS,
        str(pool),
        fake_path=fake_path,
        env={"LAUNCHES": str(launches), "SLUGS_FILE": str(slugs)},
    )

    assert result.returncode == 0, result.stderr
    doc = json.loads(pool.read_text())
    assert doc["ok"] is True
    assert [item["slug"] for item in doc["data"]["details"]] == ["agent-workbench"]
    assert doc["data"]["detail_errors"][0]["slug"] == "sales-glitter"
    assert doc["query"]["detail_slugs"] == ["agent-workbench", "sales-glitter"]
    assert doc["meta"]["detail_count"] == 1
    assert doc["meta"]["detail_error_count"] == 1


def test_fetch_details_rejects_slug_outside_launch_pool(tmp_path: Path, fake_path: Path):
    launches = tmp_path / "launches.json"
    pool = tmp_path / "pool.json"
    slugs = tmp_path / "slugs.txt"
    slugs.write_text("outside-pool\n")

    first = run_script(FETCH_LAUNCHES, str(launches), fake_path=fake_path)
    assert first.returncode == 0, first.stderr

    result = run_script(
        FETCH_DETAILS,
        str(pool),
        fake_path=fake_path,
        env={"LAUNCHES": str(launches), "SLUGS_FILE": str(slugs)},
    )

    assert result.returncode != 0
    assert "not present in launch pool" in result.stderr
