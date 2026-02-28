"""Trigger user digest collection command."""

import click
from uuid import UUID
from xndctl.cli import pass_context, Context
from xndctl.utils import handle_error, display_success, display_warning, display_info, console
from xndctl.prompts.subscription import prompt_select_user


@click.command(name="trigger")
@click.option("-p", "--prompt", is_flag=True, required=True, help="Interactive mode (required)")
@pass_context
def trigger(ctx: Context, prompt: bool):
    """Manually trigger digest collection for a user (interactive only).

    This command triggers the full digest pipeline for a user:
    1. Collects data from all topics associated with the user
    2. Generates an aggregated digest
    3. Sends notifications via configured channels (Feishu/Email)
    """
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
                f"[yellow]Warning:[/yellow] User '{selected_user.name or selected_user.email}' has no topics configured."
            )
            console.print("Add topics to the user's topics list first.")
            return

        console.print(f"[bold]User: {selected_user.name or selected_user.email}[/bold]")
        console.print(f"[dim]Topics configured: {len(selected_user.topics)}[/dim]")
        click.echo()

        topics_info = []
        for topic_id_str in selected_user.topics:
            try:
                topic_id = UUID(topic_id_str) if isinstance(topic_id_str, str) else topic_id_str
                topic = ctx.client.get_topic(topic_id)
                status = "[green]enabled[/green]" if topic.is_enabled else "[red]disabled[/red]"
                topics_info.append(f"  - {topic.name} ({status})")
            except Exception:
                topics_info.append(f"  - {topic_id_str} ([yellow]not found[/yellow])")

        console.print("[bold]Topics to collect:[/bold]")
        for info in topics_info:
            click.echo(info)

        click.echo()
        if not click.confirm("Trigger digest collection for this user?", default=True):
            display_warning("Trigger cancelled")
            return

        display_info(f"Triggering digest collection for user: {selected_user.name or selected_user.email}")
        result = ctx.client.trigger_user(selected_user_id)

        display_success(f"Digest collection triggered: {result.message}")
        if result.task_id:
            click.echo(f"Task ID: {result.task_id}")
        if result.user_id:
            click.echo(f"User ID: {result.user_id}")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)
