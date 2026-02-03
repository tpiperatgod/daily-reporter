"""Notify digest command."""

import click
from uuid import UUID
from typing import List, Optional
from xndctl.cli import pass_context, Context
from xndctl.schemas import DigestWithDetails
from xndctl.utils import (
    handle_error,
    display_success,
    display_warning,
    display_info,
    truncate_text
)


def prompt_select_digest(digests: List[DigestWithDetails]) -> Optional[UUID]:
    """Prompt to select a digest from list.

    Args:
        digests: List of available digests

    Returns:
        Selected digest ID or None if cancelled
    """
    click.echo()
    click.echo("[bold]Select Digest:[/bold]")
    for i, digest in enumerate(digests, 1):
        # Extract headline from summary_json
        headline = "No headline"
        if isinstance(digest.summary_json, dict) and "headline" in digest.summary_json:
            headline = digest.summary_json["headline"]

        topic_name = digest.topic.name if digest.topic else "Unknown"
        time_range = f"{digest.time_window_start.date()} to {digest.time_window_end.date()}"

        click.echo(f"  {i}. [{topic_name}] {truncate_text(headline, 60)}")
        click.echo(f"      Time: {time_range} | Deliveries: {len(digest.deliveries)}")

    while True:
        try:
            digest_input = click.prompt("\nSelect digest (number, 0 to cancel)", type=int)
            if digest_input == 0:
                return None
            if 1 <= digest_input <= len(digests):
                return digests[digest_input - 1].id
            click.echo(f"[red]Invalid selection. Choose 0-{len(digests)}[/red]")
        except Exception:
            click.echo(f"[red]Invalid input. Enter a number 0-{len(digests)}[/red]")


def prompt_select_subscription(subscriptions: List) -> Optional[UUID]:
    """Prompt to select a subscription from list.

    Args:
        subscriptions: List of available subscriptions

    Returns:
        Selected subscription ID or None if cancelled
    """
    click.echo()
    click.echo("[bold]Select Subscription:[/bold]")
    for i, sub in enumerate(subscriptions, 1):
        user_name = f"{sub.user.name or '(no name)'} ({sub.user.email})"
        topic_name = sub.topic.name
        channels = []
        if sub.enable_feishu:
            channels.append("feishu")
        if sub.enable_email:
            channels.append("email")

        click.echo(f"  {i}. {user_name} → {topic_name} ({', '.join(channels)})")

    while True:
        try:
            sub_input = click.prompt("\nSelect subscription (number, 0 to cancel)", type=int)
            if sub_input == 0:
                return None
            if 1 <= sub_input <= len(subscriptions):
                return subscriptions[sub_input - 1].id
            click.echo(f"[red]Invalid selection. Choose 0-{len(subscriptions)}[/red]")
        except Exception:
            click.echo(f"[red]Invalid input. Enter a number 0-{len(subscriptions)}[/red]")


@click.command(name="notify")
@click.option("-p", "--prompt", is_flag=True, required=True, help="Interactive mode (required)")
@pass_context
def notify(ctx: Context, prompt: bool):
    """Manually send digest notification (interactive only)."""
    try:
        # Fetch digests
        digests_result = ctx.client.list_digests(limit=100)

        if not digests_result.items:
            click.echo("[red]Error:[/red] No digests found. Trigger topic collection first.")
            return

        display_info(f"Found {len(digests_result.items)} recent digests")

        # Interactive digest selection
        selected_digest_id = prompt_select_digest(digests_result.items)

        if not selected_digest_id:
            display_warning("Notification cancelled")
            return

        # Get digest details
        selected_digest = next(d for d in digests_result.items if d.id == selected_digest_id)

        # Fetch subscriptions for the digest's topic
        all_subscriptions = ctx.client.list_subscriptions(limit=1000)
        topic_subscriptions = [
            s for s in all_subscriptions.items
            if s.topic_id == selected_digest.topic_id
        ]

        if not topic_subscriptions:
            click.echo(f"[red]Error:[/red] No subscriptions found for topic '{selected_digest.topic.name}'")
            return

        display_info(f"Found {len(topic_subscriptions)} subscription(s) for this topic")

        # Interactive subscription selection
        selected_subscription_id = prompt_select_subscription(topic_subscriptions)

        if not selected_subscription_id:
            display_warning("Notification cancelled")
            return

        # Get subscription details for display
        selected_subscription = next(s for s in topic_subscriptions if s.id == selected_subscription_id)

        # Send digest
        display_info(f"Sending digest to {selected_subscription.user.email}...")
        result = ctx.client.send_digest(selected_digest_id, selected_subscription_id)

        # Display result
        display_success(f"Digest notification sent")
        click.echo()
        click.echo("[bold]Delivery Statistics:[/bold]")
        click.echo(f"  Total: {result.total_sent}")
        click.echo(f"  Successful: [green]{result.successful}[/green]")
        click.echo(f"  Failed: [red]{result.failed}[/red]")

        # Show delivery details
        if result.deliveries:
            click.echo()
            click.echo("[bold]Deliveries:[/bold]")
            for delivery in result.deliveries:
                status_color = "green" if delivery.status == "success" else "red"
                status_text = f"[{status_color}]{delivery.status}[/{status_color}]"
                click.echo(f"  • {delivery.channel}: {status_text}")
                if delivery.error_msg:
                    click.echo(f"    Error: {delivery.error_msg}")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)
