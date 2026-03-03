"""Interactive prompts for topic operations."""

import click
from xndctl.utils import console
from typing import Tuple
from xndctl.schemas import TopicCreate, TopicUpdate


def prompt_topic_create() -> Tuple[TopicCreate, bool]:
    """Interactive prompt for creating a topic.

    Returns:
        Tuple of (TopicCreate object, confirmation)
    """
    click.echo()
    console.print("[bold]Create New Topic[/bold]")
    console.print("[dim]* = required field[/dim]")
    click.echo()

    # Name (required)
    name = click.prompt("Name *", type=str)

    # Query (required)
    query = click.prompt("Query *", type=str)

    # Create topic object
    topic = TopicCreate(name=name, query=query)

    # Display summary and confirm
    click.echo()
    console.print("[bold]Topic Summary:[/bold]")
    click.echo(f"  Name: {name}")
    click.echo(f"  Query: {query}")
    click.echo()

    confirmed = click.confirm("Create this topic?", default=True)

    return topic, confirmed


def prompt_topic_update(current_name: str, current_query: str, current_enabled: bool) -> Tuple[TopicUpdate, bool]:
    """Interactive prompt for updating a topic.

    Args:
        current_name: Current topic name
        current_query: Current query
        current_enabled: Current enabled status

    Returns:
        Tuple of (TopicUpdate object, confirmation)
    """
    click.echo()
    console.print("[bold]Update Topic[/bold]")
    console.print("[dim]Press Enter to keep current value[/dim]")
    click.echo()

    # Name
    name_input = click.prompt("Name", default=current_name, show_default=True)
    name = name_input if name_input != current_name else None

    # Query
    query_input = click.prompt("Query", default=current_query, show_default=True)
    query = query_input if query_input != current_query else None

    # Enabled status
    is_enabled_input = click.confirm("Enable topic?", default=current_enabled)
    is_enabled = is_enabled_input if is_enabled_input != current_enabled else None

    # Create update object (only include changed fields)
    update = TopicUpdate(name=name, query=query, is_enabled=is_enabled)

    # Check if anything changed
    if not any([name, query, is_enabled is not None]):
        console.print("[yellow]No changes specified[/yellow]")
        return update, False

    # Display summary and confirm
    click.echo()
    console.print("[bold]Changes:[/bold]")
    if name:
        click.echo(f"  Name: {name}")
    if query:
        click.echo(f"  Query: {query}")
    if is_enabled is not None:
        click.echo(f"  Enabled: {is_enabled}")
    click.echo()

    confirmed = click.confirm("Apply these changes?", default=True)

    return update, confirmed
