"""Output and packaging contract tests for drm."""

from __future__ import annotations

from pathlib import Path

from drm.dashboard_data import build_dashboard_model_from_data, load_dashboard_data
from drm.templates import render_dashboard_html


def test_pyproject_registers_drm_package_and_script() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '"drm*"' in pyproject
    assert 'drm = "drm.cli:cli"' in pyproject


def test_curated_fixture_builds_dashboard_html() -> None:
    data = load_dashboard_data(Path("tests/drm/fixtures/dashboard-data-valid.json"))
    model = build_dashboard_model_from_data(data)
    html = render_dashboard_html(model)

    assert "HN 高价值内容报告" in html
    assert "DeepSeek" in html
    assert model.search_index
