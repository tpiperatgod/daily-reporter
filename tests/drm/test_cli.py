"""Tests for the drm Click CLI."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from drm.cli import cli


def test_cli_help_exits_zero() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Daily Report Manager" in result.output
    assert "dashboard" in result.output


def test_dashboard_help_exits_zero() -> None:
    result = CliRunner().invoke(cli, ["dashboard", "--help"])

    assert result.exit_code == 0
    assert "build" in result.output


def test_dashboard_build_writes_output_from_curated_json(tmp_path: Path) -> None:
    input_path = tmp_path / "dashboard-data.json"
    output = tmp_path / "dashboard" / "index.html"
    input_path.write_text(
        Path("tests/drm/fixtures/dashboard-data-valid.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        ["dashboard", "build", "--input", str(input_path), "--output", str(output)],
    )

    assert result.exit_code == 0, result.stderr
    assert output.exists()
    assert "Built" in result.output
    assert "Reports: 1 available" in result.output
    assert "DeepSeek V4" in output.read_text(encoding="utf-8")


def test_dashboard_build_missing_input_exits_2(tmp_path: Path) -> None:
    output = tmp_path / "dashboard.html"

    result = CliRunner().invoke(
        cli,
        ["dashboard", "build", "--input", str(tmp_path / "missing.json"), "--output", str(output)],
    )

    assert result.exit_code == 2
    assert "dashboard data input does not exist" in result.stderr
    assert not output.exists()


def test_dashboard_build_invalid_json_exits_2(tmp_path: Path) -> None:
    input_path = tmp_path / "bad.json"
    output = tmp_path / "dashboard.html"
    input_path.write_text("{not-json", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["dashboard", "build", "--input", str(input_path), "--output", str(output)],
    )

    assert result.exit_code == 2
    assert "invalid dashboard data JSON" in result.stderr
    assert not output.exists()


def test_dashboard_build_unknown_template_exits_2(tmp_path: Path) -> None:
    input_path = tmp_path / "dashboard-data.json"
    output = tmp_path / "dashboard.html"
    input_path.write_text(
        Path("tests/drm/fixtures/dashboard-data-valid.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "dashboard",
            "build",
            "--input",
            str(input_path),
            "--output",
            str(output),
            "--template",
            "fancy",
        ],
    )

    assert result.exit_code == 2
    assert "unknown dashboard template" in result.stderr
