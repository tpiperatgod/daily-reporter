"""Click entrypoint for drm CLI."""

from __future__ import annotations

from pathlib import Path

import click

from drm.dashboard_data import build_dashboard_model_from_data, load_dashboard_data
from drm.errors import DRMError, InputError, OutputError
from drm.templates import render_dashboard_html


@click.group()
def cli() -> None:
    """Daily Report Manager."""


@cli.group()
def dashboard() -> None:
    """Build and manage daily report dashboards."""


@dashboard.command()
@click.option(
    "--input",
    "input_path",
    type=click.Path(path_type=Path),
    default=Path("docs/dashboard/dashboard-data.json"),
    show_default=True,
    help="Curated dashboard data JSON file.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("docs/dashboard/index.html"),
    show_default=True,
    help="Path to write the generated dashboard HTML.",
)
@click.option("--template", default="default", show_default=True, help="Dashboard template name.")
def build(input_path: Path, output: Path, template: str) -> None:
    """Build the static dashboard from curated JSON."""
    try:
        if template != "default":
            raise InputError(f"unknown dashboard template: {template}")
        data = load_dashboard_data(input_path)
        model = build_dashboard_model_from_data(data)
        html = render_dashboard_html(model)
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(html, encoding="utf-8")
        except OSError as exc:
            raise OutputError(f"could not write output: {output}") from exc
    except DRMError as err:
        click.echo(str(err), err=True)
        raise SystemExit(err.exit_code) from err

    available_count = sum(
        1
        for reports in model.reports_by_date.values()
        for report in reports.values()
        if report.get("status") == "available"
    )
    incomplete_count = sum(
        1
        for reports in model.reports_by_date.values()
        for report in reports.values()
        if report.get("status") == "incomplete"
    )
    block_count = sum(
        len(report.get("selected_blocks", []) or [])
        for reports in model.reports_by_date.values()
        for report in reports.values()
    )
    click.echo(f"Built {output}")
    click.echo(
        f"Reports: {available_count} available, {incomplete_count} incomplete, "
        f"{block_count} selected blocks, {len(model.dates)} dates"
    )
