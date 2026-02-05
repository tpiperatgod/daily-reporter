"""Subscription management commands."""

import click
from uuid import UUID
from xndctl.cli import pass_context, Context
from xndctl.schemas import SubscriptionCreate
from xndctl.utils import (
    display_paginated_results,
    display_output,
    handle_error,
    confirm_action,
    display_success,
    display_warning,
    console
)
from xndctl.prompts.subscription import prompt_subscription_create
from xndctl.client import NotFoundError


@click.group(name="sub")
def sub():
    """Manage subscriptions."""
    pass


@sub.command(name="create")
@click.option("-p", "--prompt", is_flag=True, required=True, help="Interactive mode (required)")
@pass_context
def create(ctx: Context, prompt: bool):
    """Create a new subscription (interactive only)."""
    try:
        # Fetch users and topics
        users_result = ctx.client.list_users(limit=1000)
        topics_result = ctx.client.list_topics(limit=1000)

        if not users_result.items:
            console.print("[red]Error:[/red] No users found. Create a user first.")
            return

        if not topics_result.items:
            console.print("[red]Error:[/red] No topics found. Create a topic first.")
            return

        # Interactive mode
        subscription_data, confirmed = prompt_subscription_create(
            users_result.items,
            topics_result.items
        )

        if not confirmed:
            display_warning("Subscription creation cancelled")
            return

        # Create subscription
        result = ctx.client.create_subscription(subscription_data)
        display_success(f"Subscription created (ID: {result.id})")

        # Display full details
        if ctx.output_format == "table":
            click.echo()
            # Fetch full details
            full_sub = ctx.client.get_subscription(result.id)
            display_output(full_sub, format=ctx.output_format)

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@sub.command(name="ls")
@click.option("--limit", default=100, help="Number of items to show")
@click.option("--offset", default=0, help="Offset for pagination")
@click.option("--user-id", help="Filter by user ID")
@click.option("--topic-id", help="Filter by topic ID")
@pass_context
def list_subscriptions(ctx: Context, limit: int, offset: int, user_id: str, topic_id: str):
    """List all subscriptions."""
    try:
        result = ctx.client.list_subscriptions(limit=limit, offset=offset)

        # Apply client-side filters if needed (API doesn't support filtering yet)
        items = result.items
        if user_id:
            items = [s for s in items if str(s.user_id) == user_id]
        if topic_id:
            items = [s for s in items if str(s.topic_id) == topic_id]

        # Format for display
        display_items = []
        for sub in items:
            channels = []
            if sub.enable_feishu:
                channels.append("feishu")
            if sub.enable_email:
                channels.append("email")

            display_items.append({
                "id": str(sub.id),
                "user": f"{sub.user.name or '(no name)'} ({sub.user.email})",
                "topic": sub.topic.name,
                "channels": ", ".join(channels),
                "created_at": sub.created_at
            })

        # Prepare display columns
        columns = ["id", "user", "topic", "channels", "created_at"]

        if ctx.output_format == "table":
            display_paginated_results(
                items=display_items,
                total=len(display_items),
                limit=limit,
                offset=0,
                has_more=False,
                format=ctx.output_format,
                columns=columns,
                title="Subscriptions"
            )
        else:
            # For JSON/YAML, show full objects
            display_output(items, format=ctx.output_format)

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@sub.command(name="get")
@click.option("--id", "subscription_id", required=True, help="Subscription ID")
@pass_context
def get_subscription(ctx: Context, subscription_id: str):
    """Get subscription details."""
    try:
        subscription = ctx.client.get_subscription(UUID(subscription_id))
        display_output(subscription, format=ctx.output_format, title="Subscription Details")

        # Show additional info in table format
        if ctx.output_format == "table":
            click.echo()
            console.print("[bold]User:[/bold]")
            click.echo(f"  Name: {subscription.user.name or '(no name)'}")
            click.echo(f"  Email: {subscription.user.email}")
            click.echo()
            console.print("[bold]Topic:[/bold]")
            click.echo(f"  Name: {subscription.topic.name}")
            click.echo(f"  Query: {subscription.topic.query}")
            click.echo(f"  Schedule: {subscription.topic.cron_expression}")
            click.echo()
            console.print("[bold]Notification Channels:[/bold]")
            console.print(f"  Feishu: {'[green]Enabled[/green]' if subscription.enable_feishu else '[red]Disabled[/red]'}")
            console.print(f"  Email: {'[green]Enabled[/green]' if subscription.enable_email else '[red]Disabled[/red]'}")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@sub.command(name="delete")
@click.option("--id", "subscription_id", required=True, help="Subscription ID")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
@pass_context
def delete(ctx: Context, subscription_id: str, yes: bool):
    """Delete a subscription."""
    try:
        # Get subscription details
        subscription = ctx.client.get_subscription(UUID(subscription_id))

        # Show subscription info
        click.echo(f"Subscription ID: {subscription.id}")
        click.echo(f"User: {subscription.user.name or '(no name)'} ({subscription.user.email})")
        click.echo(f"Topic: {subscription.topic.name}")
        channels = []
        if subscription.enable_feishu:
            channels.append("feishu")
        if subscription.enable_email:
            channels.append("email")
        click.echo(f"Channels: {', '.join(channels)}")

        # Confirm deletion
        if not yes:
            if not confirm_action("Delete this subscription?", default=False):
                display_warning("Deletion cancelled")
                return

        # Delete subscription
        ctx.client.delete_subscription(subscription.id)
        display_success("Subscription deleted")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)
