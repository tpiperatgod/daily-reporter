"""Interactive prompts for subscription operations."""

import click
from typing import List, Tuple, Optional
from uuid import UUID
from xndctl.schemas import SubscriptionCreate, UserWithSubscriptions, TopicWithStats


def prompt_subscription_create(
    users: List[UserWithSubscriptions],
    topics: List[TopicWithStats]
) -> Tuple[SubscriptionCreate, bool]:
    """Interactive prompt for creating a subscription.

    Args:
        users: List of available users
        topics: List of available topics

    Returns:
        Tuple of (SubscriptionCreate object, confirmation)
    """
    click.echo()
    click.echo("[bold]Create New Subscription[/bold]")
    click.echo()

    # Select user
    click.echo("[bold]Available Users:[/bold]")
    for i, user in enumerate(users, 1):
        display_name = user.name or "(no name)"
        click.echo(f"  {i}. {display_name} ({user.email})")

    while True:
        try:
            user_idx = click.prompt("\nSelect user (number)", type=int)
            if 1 <= user_idx <= len(users):
                selected_user = users[user_idx - 1]
                break
            click.echo(f"[red]Invalid selection. Choose 1-{len(users)}[/red]")
        except Exception:
            click.echo(f"[red]Invalid input. Enter a number 1-{len(users)}[/red]")

    # Select topic
    click.echo()
    click.echo("[bold]Available Topics:[/bold]")
    for i, topic in enumerate(topics, 1):
        status = "[green]enabled[/green]" if topic.is_enabled else "[red]disabled[/red]"
        click.echo(f"  {i}. {topic.name} - {topic.query} ({status})")

    while True:
        try:
            topic_idx = click.prompt("\nSelect topic (number)", type=int)
            if 1 <= topic_idx <= len(topics):
                selected_topic = topics[topic_idx - 1]
                break
            click.echo(f"[red]Invalid selection. Choose 1-{len(topics)}[/red]")
        except Exception:
            click.echo(f"[red]Invalid input. Enter a number 1-{len(topics)}[/red]")

    # Select notification channels
    click.echo()
    click.echo("[bold]Notification Channels:[/bold]")
    enable_feishu = click.confirm("Enable Feishu notifications?", default=True)
    enable_email = click.confirm("Enable Email notifications?", default=True)

    if not enable_feishu and not enable_email:
        click.echo("[yellow]Warning: No notification channels enabled[/yellow]")

    # Create subscription object
    subscription = SubscriptionCreate(
        user_id=selected_user.id,
        topic_id=selected_topic.id,
        enable_feishu=enable_feishu,
        enable_email=enable_email
    )

    # Display summary and confirm
    click.echo()
    click.echo("[bold]Subscription Summary:[/bold]")
    click.echo(f"  User: {selected_user.name or '(no name)'} ({selected_user.email})")
    click.echo(f"  Topic: {selected_topic.name}")
    channels = []
    if enable_feishu:
        channels.append("Feishu")
    if enable_email:
        channels.append("Email")
    click.echo(f"  Channels: {', '.join(channels) if channels else 'None'}")
    click.echo()

    confirmed = click.confirm("Create this subscription?", default=True)

    return subscription, confirmed


def prompt_select_user(users: List[UserWithSubscriptions]) -> Optional[UUID]:
    """Prompt to select a user from list.

    Args:
        users: List of available users

    Returns:
        Selected user ID or None if cancelled
    """
    click.echo()
    click.echo("[bold]Select User:[/bold]")
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
            click.echo(f"[red]Invalid selection. Choose 0-{len(users)}[/red]")
        except Exception:
            click.echo(f"[red]Invalid input. Enter a number 0-{len(users)}[/red]")


def prompt_select_topic(topics: List[TopicWithStats]) -> Optional[UUID]:
    """Prompt to select a topic from list.

    Args:
        topics: List of available topics

    Returns:
        Selected topic ID or None if cancelled
    """
    click.echo()
    click.echo("[bold]Select Topic:[/bold]")
    for i, topic in enumerate(topics, 1):
        status = "[green]enabled[/green]" if topic.is_enabled else "[red]disabled[/red]"
        click.echo(f"  {i}. {topic.name} - {topic.query} ({status})")

    while True:
        try:
            topic_input = click.prompt("\nSelect topic (number, 0 to cancel)", type=int)
            if topic_input == 0:
                return None
            if 1 <= topic_input <= len(topics):
                return topics[topic_input - 1].id
            click.echo(f"[red]Invalid selection. Choose 0-{len(topics)}[/red]")
        except Exception:
            click.echo(f"[red]Invalid input. Enter a number 0-{len(topics)}[/red]")
