"""Interactive prompts for topic operations."""

import click
from typing import Tuple
from xndctl.schemas import TopicCreate, TopicUpdate
from xndctl.utils import validate_cron_expression


def prompt_topic_create() -> Tuple[TopicCreate, bool]:
    """Interactive prompt for creating a topic.

    Returns:
        Tuple of (TopicCreate object, confirmation)
    """
    click.echo()
    click.echo("[bold]Create New Topic[/bold]")
    click.echo("[dim]* = required field[/dim]")
    click.echo()

    # Name (required)
    name = click.prompt("Name *", type=str)

    # Query (required)
    query = click.prompt("Query *", type=str)

    # Cron expression (required, with validation)
    click.echo()
    click.echo("[dim]Cron format: minute hour day month weekday[/dim]")
    click.echo("[dim]Example: '0 8 * * *' (daily at 8:00 AM)[/dim]")
    click.echo()

    while True:
        cron_expression = click.prompt("Cron Expression *", type=str)
        if validate_cron_expression(cron_expression):
            break
        click.echo("[red]Invalid cron expression. Expected format: 'minute hour day month weekday'[/red]")
        click.echo("[dim]Example: '0 8 * * *' (daily at 8:00 AM)[/dim]")

    # Create topic object
    topic = TopicCreate(
        name=name,
        query=query,
        cron_expression=cron_expression
    )

    # Display summary and confirm
    click.echo()
    click.echo("[bold]Topic Summary:[/bold]")
    click.echo(f"  Name: {name}")
    click.echo(f"  Query: {query}")
    click.echo(f"  Schedule: {cron_expression}")
    click.echo()

    confirmed = click.confirm("Create this topic?", default=True)

    return topic, confirmed


def prompt_topic_update(
    current_name: str,
    current_query: str,
    current_cron: str,
    current_enabled: bool
) -> Tuple[TopicUpdate, bool]:
    """Interactive prompt for updating a topic.

    Args:
        current_name: Current topic name
        current_query: Current query
        current_cron: Current cron expression
        current_enabled: Current enabled status

    Returns:
        Tuple of (TopicUpdate object, confirmation)
    """
    click.echo()
    click.echo("[bold]Update Topic[/bold]")
    click.echo("[dim]Press Enter to keep current value[/dim]")
    click.echo()

    # Name
    name_input = click.prompt(
        "Name",
        default=current_name,
        show_default=True
    )
    name = name_input if name_input != current_name else None

    # Query
    query_input = click.prompt(
        "Query",
        default=current_query,
        show_default=True
    )
    query = query_input if query_input != current_query else None

    # Cron expression (with validation)
    click.echo()
    click.echo("[dim]Cron format: minute hour day month weekday[/dim]")
    cron_expression = None
    while True:
        cron_input = click.prompt(
            "Cron Expression",
            default=current_cron,
            show_default=True
        )
        if cron_input == current_cron:
            break
        if validate_cron_expression(cron_input):
            cron_expression = cron_input
            break
        click.echo("[red]Invalid cron expression[/red]")

    # Enabled status
    is_enabled_input = click.confirm(
        "Enable topic?",
        default=current_enabled
    )
    is_enabled = is_enabled_input if is_enabled_input != current_enabled else None

    # Create update object (only include changed fields)
    update = TopicUpdate(
        name=name,
        query=query,
        cron_expression=cron_expression,
        is_enabled=is_enabled
    )

    # Check if anything changed
    if not any([name, query, cron_expression, is_enabled is not None]):
        click.echo("[yellow]No changes specified[/yellow]")
        return update, False

    # Display summary and confirm
    click.echo()
    click.echo("[bold]Changes:[/bold]")
    if name:
        click.echo(f"  Name: {name}")
    if query:
        click.echo(f"  Query: {query}")
    if cron_expression:
        click.echo(f"  Schedule: {cron_expression}")
    if is_enabled is not None:
        click.echo(f"  Enabled: {is_enabled}")
    click.echo()

    confirmed = click.confirm("Apply these changes?", default=True)

    return update, confirmed
