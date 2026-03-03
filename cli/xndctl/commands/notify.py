"""Notify command - deprecated."""

import click
from xndctl.context import pass_context, Context
from xndctl.utils import console


@click.command(name="notify")
@pass_context
def notify(ctx: Context):
    """Send digest notifications (DEPRECATED)."""
    console.print("[yellow]Warning:[/yellow] The 'notify' command is deprecated.")
    console.print("Digest notifications are now sent automatically after user trigger.")
    console.print()
    console.print("Use [bold]xndctl trigger -p[/bold] to trigger collection and notification.")
