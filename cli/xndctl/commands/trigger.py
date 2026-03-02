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

        # FIX: Use subscriptions instead of topics
        if not selected_user.subscriptions or len(selected_user.subscriptions) == 0:
            console.print(
                f"[yellow]Warning:[/yellow] User '{selected_user.name or selected_user.email}' has no subscriptions."
            )
            console.print("Create subscriptions to link this user to topics first.")
            return

        console.print(f"[bold]User: {selected_user.name or selected_user.email}[/bold]")
        console.print(f"[dim]Subscriptions: {len(selected_user.subscriptions)}[/dim]")
        click.echo()

        # FIX: Iterate subscriptions to get topics (already loaded, no extra API calls)
        topics_info = []
        topic_ids = []
        for sub in selected_user.subscriptions:
            if sub.topic:
                topic_ids.append(sub.topic.id)
                status = "[green]enabled[/green]" if sub.topic.is_enabled else "[red]disabled[/red]"
                topics_info.append(f"  - {sub.topic.name} ({status})")
            else:
                topics_info.append(f"  - {sub.topic_id} ([yellow]topic not loaded[/yellow])")

        console.print("[bold]Topics to collect:[/bold]")
        for info in topics_info:
            click.echo(info)

        click.echo()
        if not click.confirm("Trigger digest collection for this user?", default=True):
            display_warning("Trigger cancelled")
            return

        display_info(f"Triggering digest collection for user: {selected_user.name or selected_user.email}")

        # Trigger user collection (single API call)
        result = ctx.client.trigger_user(selected_user_id)
        task_id = result.task_id

        display_success(f"Digest collection triggered for user: {selected_user.name or selected_user.email}")
        console.print(f"[dim]Topics: {result.topic_count}[/dim]")
        console.print(f"[dim]Task ID: {task_id}[/dim]")
        console.print(f"[dim]User ID: {selected_user_id}[/dim]")
    except Exception as e:
        handle_error(e, verbose=ctx.verbose)
