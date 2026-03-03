"""Utility functions for display, formatting, and error handling."""

import json
import sys
import click
from typing import Any, Dict, List, Optional
import yaml
from rich.console import Console
from rich.table import Table
from rich import box


# Console instances for output
console = Console()
console_err = Console(stderr=True)



def display_table(data: List[Dict[str, Any]], columns: Optional[List[str]] = None, title: Optional[str] = None) -> None:
    """Display data as a rich table.

    Args:
        data: List of dictionaries to display
        columns: Optional list of column names to display (in order). If None, uses all keys from first item.
        title: Optional table title
    """
    if not data:
        console.print("[yellow]No data to display[/yellow]")
        return

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    # Create table
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold cyan")

    # Add columns
    for col in columns:
        table.add_column(col.replace("_", " ").title(), overflow="fold")

    # Add rows
    for item in data:
        row = []
        for col in columns:
            value = item.get(col)
            if value is None:
                row.append("[dim]None[/dim]")
            elif isinstance(value, bool):
                row.append("[green]Yes[/green]" if value else "[red]No[/red]")
            elif isinstance(value, (list, dict)):
                row.append(str(value)[:50] + "..." if len(str(value)) > 50 else str(value))
            else:
                row.append(str(value))
        table.add_row(*row)

    console.print(table)


def display_json(data: Any) -> None:
    """Display data as formatted JSON."""
    console.print_json(json.dumps(data, default=str, indent=2))


def display_yaml(data: Any) -> None:
    """Display data as formatted YAML."""
    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
    console.print(yaml_str)


def display_output(data: Any, format: str = "table", columns: Optional[List[str]] = None, title: Optional[str] = None) -> None:
    """Universal output formatter.

    Args:
        data: Data to display (dict, list, or Pydantic model)
        format: Output format (table, json, yaml)
        columns: Optional list of columns for table format
        title: Optional title for table format
    """
    # Convert Pydantic models to dict
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
        data = [item.model_dump(mode="json") for item in data]

    if format == "json":
        display_json(data)
    elif format == "yaml":
        display_yaml(data)
    else:  # table
        if isinstance(data, list):
            display_table(data, columns=columns, title=title)
        elif isinstance(data, dict):
            display_table([data], columns=columns, title=title)
        else:
            console.print(str(data))


def display_paginated_results(
    items: List[Any],
    total: int,
    limit: int,
    offset: int,
    has_more: bool,
    format: str = "table",
    columns: Optional[List[str]] = None,
    title: Optional[str] = None
) -> None:
    """Display paginated results with metadata.

    Args:
        items: List of items to display
        total: Total number of items
        limit: Items per page
        offset: Current offset
        has_more: Whether there are more items
        format: Output format
        columns: Optional columns for table format
        title: Optional title for table format
    """
    # Display items
    display_output(items, format=format, columns=columns, title=title)

    # Display pagination metadata (only for table format)
    if format == "table":
        console.print()
        current_page = (offset // limit) + 1
        total_pages = (total + limit - 1) // limit
        console.print(f"[dim]Page {current_page}/{total_pages} | Showing {len(items)} of {total} items[/dim]")
        if has_more:
            console.print(f"[dim]Use --offset {offset + limit} to see more[/dim]")


def handle_error(error: Exception, verbose: bool = False) -> None:
    """Centralized error handler.

    Args:
        error: Exception to handle
        verbose: Whether to show detailed error information
    """
    from xndctl.client import APIError, NotFoundError, ValidationError

    if isinstance(error, NotFoundError):
        console_err.print(f"[red]Error:[/red] {str(error)}")
    elif isinstance(error, ValidationError):
        console_err.print(f"[red]Validation Error:[/red] {str(error)}")
    elif isinstance(error, APIError):
        console_err.print(f"[red]API Error:[/red] {str(error)}")
    else:
        console_err.print(f"[red]Error:[/red] {str(error)}")

    if verbose:
        console_err.print("\n[yellow]Detailed error information:[/yellow]")
        import traceback
        console_err.print(traceback.format_exc())

    sys.exit(1)


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt for confirmation.

    Args:
        message: Confirmation message
        default: Default value

    Returns:
        True if confirmed, False otherwise
    """
    return click.confirm(message, default=default)


def format_datetime(dt: Any) -> str:
    """Format datetime for display."""
    if dt is None:
        return "Never"
    return str(dt).split(".")[0]  # Remove microseconds


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def display_success(message: str) -> None:
    """Display success message."""
    console.print(f"[green]✓[/green] {message}")


def display_info(message: str) -> None:
    """Display info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def display_warning(message: str) -> None:
    """Display warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")
