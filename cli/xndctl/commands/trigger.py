"""Trigger user digest collection command."""

import click
from uuid import UUID
from typing import List, Optional
from xndctl.context import pass_context, Context
from xndctl.utils import handle_error, display_success, display_warning, display_info, console
from xndctl.schemas import UserWithTopics



def prompt_time_window() -> str:
    """Prompt user to select time window for data collection."""
    click.echo()
    console.print("[bold]Select Time Window:[/bold]")
    click.echo("  1. 4h  - Last 4 hours")
    click.echo("  2. 12h - Last 12 hours")
    click.echo("  3. 24h - Last 24 hours (default)")

    while True:
        try:
            user_input = click.prompt("\nSelect time window (1-3)", type=int, default=3)
            if user_input == 1:
                return "4h"
            elif user_input == 2:
                return "12h"
            elif user_input == 3:
                return "24h"
            console.print("[red]Invalid selection. Choose 1-3[/red]")
        except Exception:
            console.print("[red]Invalid input. Enter a number 1-3[/red]")


def prompt_select_user(users: List[UserWithTopics]) -> Optional[UUID]:
    click.echo()
    console.print("[bold]Select User:[/bold]")
    for i, user in enumerate(users, 1):
        display_name = user.name or "(no name)"
        click.echo(f"  {i}. {display_name} ({user.email})")

    while True:
        try:
            user_input = click.prompt("\nSelect user (number, 0 to cancel)", type=int)
            if user_input == 0:
                return None
            if 1 <= user_input <= len(users):
                return users[user_input - 1].id
            console.print(f"[red]Invalid selection. Choose 0-{len(users)}[/red]")
        except Exception:
            console.print(f"[red]Invalid input. Enter a number 0-{len(users)}[/red]")


@click.command(name="trigger")
@click.option("-p", "--prompt", is_flag=True, required=True, help="Interactive mode (required)")
@click.option(
    "-t", "--time-window",
    type=click.Choice(["4h", "12h", "24h", "1d"], case_sensitive=True),
    default=None,
    help="Time window for data collection (default: 24h)"
)
@pass_context
def trigger(ctx: Context, prompt: bool, time_window: Optional[str]):

    try:
        users_result = ctx.client.list_users(limit=1000)

        if not users_result.items:
            console.print("[red]Error:[/red] No users found. Create a user first.")
            return

        display_info(f"Found {len(users_result.items)} users")

        selected_user_id = prompt_select_user(users_result.items)

        if not selected_user_id:
            display_warning("Trigger cancelled")
            return

        selected_user = ctx.client.get_user(selected_user_id)

        if not selected_user.topics or len(selected_user.topics) == 0:
            console.print(
                f"[yellow]Warning:[/yellow] User '{selected_user.name or selected_user.email}' has no topics."
            )
            console.print("Add topics to this user first.")
            return

        console.print(f"[bold]User: {selected_user.name or selected_user.email}[/bold]")
        console.print(f"[dim]Topics: {len(selected_user.topics)}[/dim]")
        click.echo()

        topics_info = []
        for topic_id_str in selected_user.topics:
            try:
                topic = ctx.client.get_topic(UUID(topic_id_str))
                status = "[green]enabled[/green]" if topic.is_enabled else "[red]disabled[/red]"
                topics_info.append(f"  - {topic.name} ({status})")
            except Exception:
                topics_info.append(f"  - {topic_id_str} ([yellow]topic not found[/yellow])")

        console.print("[bold]Topics to collect:[/bold]")
        for info in topics_info:
            click.echo(info)

        click.echo()
        if not click.confirm("Trigger digest collection for this user?", default=True):
            display_warning("Trigger cancelled")
            return

        # Determine time window
        if time_window is None:
            time_window = prompt_time_window()

        # Normalize 1d to 24h
        if time_window == "1d":
            time_window = "24h"

        display_info(f"Triggering digest collection for user: {selected_user.name or selected_user.email}")
        display_info(f"Time window: {time_window}")

        result = ctx.client.trigger_user(selected_user_id, time_window=time_window)
        task_id = result.task_id

        display_success(f"Digest collection triggered for user: {selected_user.name or selected_user.email}")
        console.print(f"[dim]Topics: {result.topic_count}[/dim]")
        console.print(f"[dim]Time Window: {time_window}[/dim]")
        console.print(f"[dim]Task ID: {task_id}[/dim]")
        console.print(f"[dim]User ID: {selected_user_id}[/dim]")
    except Exception as e:
        handle_error(e, verbose=ctx.verbose)
