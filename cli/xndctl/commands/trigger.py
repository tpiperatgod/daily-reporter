"""Trigger topic collection command."""

import click
from uuid import UUID
from xndctl.cli import pass_context, Context
from xndctl.utils import (
    handle_error,
    display_success,
    display_warning,
    display_info
)
from xndctl.prompts.subscription import prompt_select_topic


@click.command(name="trigger")
@click.option("-p", "--prompt", is_flag=True, required=True, help="Interactive mode (required)")
@pass_context
def trigger(ctx: Context, prompt: bool):
    """Manually trigger topic collection (interactive only)."""
    try:
        # Fetch topics
        topics_result = ctx.client.list_topics(limit=1000)

        if not topics_result.items:
            click.echo("[red]Error:[/red] No topics found. Create a topic first.")
            return

        # Show enabled topics count
        enabled_count = sum(1 for t in topics_result.items if t.is_enabled)
        display_info(f"Found {len(topics_result.items)} topics ({enabled_count} enabled)")

        # Interactive topic selection
        selected_topic_id = prompt_select_topic(topics_result.items)

        if not selected_topic_id:
            display_warning("Trigger cancelled")
            return

        # Get topic name for display
        selected_topic = next(t for t in topics_result.items if t.id == selected_topic_id)

        # Trigger collection
        display_info(f"Triggering collection for topic: {selected_topic.name}")
        result = ctx.client.trigger_topic(selected_topic_id)

        # Display result
        display_success(f"Collection triggered: {result.message}")
        if result.task_id:
            click.echo(f"Task ID: {result.task_id}")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)
