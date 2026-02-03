"""Topic management commands."""

import click
from uuid import UUID
from xndctl.cli import pass_context, Context
from xndctl.schemas import TopicCreate, TopicUpdate
from xndctl.utils import (
    display_paginated_results,
    display_output,
    handle_error,
    confirm_action,
    display_success,
    display_warning,
    validate_cron_expression
)
from xndctl.prompts.topic import prompt_topic_create, prompt_topic_update
from xndctl.client import NotFoundError, ValidationError


@click.group(name="topic")
def topic():
    """Manage topics."""
    pass


@topic.command(name="create")
@click.option("--name", help="Topic name (required)")
@click.option("--query", help="Search query (required)")
@click.option("--cron", "cron_expression", help="Cron expression (required)")
@click.option("-p", "--prompt", is_flag=True, help="Interactive mode")
@pass_context
def create(
    ctx: Context,
    name: str,
    query: str,
    cron_expression: str,
    prompt: bool
):
    """Create a new topic."""
    try:
        if prompt:
            # Interactive mode
            topic_data, confirmed = prompt_topic_create()
            if not confirmed:
                display_warning("Topic creation cancelled")
                return
        else:
            # Flag-based mode
            if not all([name, query, cron_expression]):
                click.echo("[red]Error:[/red] --name, --query, and --cron are required")
                click.echo("Use -p for interactive mode")
                return

            # Validate cron expression
            if not validate_cron_expression(cron_expression):
                raise ValidationError(
                    "Invalid cron expression. Expected format: 'minute hour day month weekday'\n"
                    "Example: '0 8 * * *' (daily at 8:00 AM)"
                )

            topic_data = TopicCreate(
                name=name,
                query=query,
                cron_expression=cron_expression
            )

        # Create topic
        result = ctx.client.create_topic(topic_data)
        display_success(f"Topic created: {result.name} (ID: {result.id})")

        # Display full details
        if ctx.output_format == "table":
            click.echo()
            display_output(result, format=ctx.output_format)

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@topic.command(name="ls")
@click.option("--limit", default=100, help="Number of items to show")
@click.option("--offset", default=0, help="Offset for pagination")
@pass_context
def list_topics(ctx: Context, limit: int, offset: int):
    """List all topics."""
    try:
        result = ctx.client.list_topics(limit=limit, offset=offset)

        # Prepare display columns
        columns = ["id", "name", "query", "cron_expression", "is_enabled", "last_collection_timestamp", "total_subscriptions"]

        display_paginated_results(
            items=result.items,
            total=result.total,
            limit=result.limit,
            offset=result.offset,
            has_more=result.has_more,
            format=ctx.output_format,
            columns=columns,
            title="Topics"
        )

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@topic.command(name="get")
@click.option("--id", "topic_id", help="Topic ID")
@click.option("--name", help="Topic name")
@pass_context
def get_topic(ctx: Context, topic_id: str, name: str):
    """Get topic details."""
    try:
        # Find topic by ID or name
        if topic_id:
            topic = ctx.client.get_topic(UUID(topic_id))
        elif name:
            topic = ctx.client.find_topic_by_name(name)
            if not topic:
                raise NotFoundError(f"Topic with name '{name}' not found")
        else:
            click.echo("[red]Error:[/red] Specify --id or --name")
            return

        display_output(topic, format=ctx.output_format, title="Topic Details")

        # Show statistics if in table format
        if ctx.output_format == "table":
            click.echo()
            click.echo("[bold]Statistics:[/bold]")
            click.echo(f"  Total Items: {topic.total_items}")
            click.echo(f"  Total Digests: {topic.total_digests}")
            click.echo(f"  Total Subscriptions: {topic.total_subscriptions}")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@topic.command(name="update")
@click.option("--id", "topic_id", help="Topic ID")
@click.option("--name", "lookup_name", help="Topic name (for lookup)")
@click.option("--new-name", help="New name")
@click.option("--query", help="New query")
@click.option("--cron", "cron_expression", help="New cron expression")
@click.option("--enable/--disable", default=None, help="Enable or disable topic")
@click.option("-p", "--prompt", is_flag=True, help="Interactive mode")
@pass_context
def update(
    ctx: Context,
    topic_id: str,
    lookup_name: str,
    new_name: str,
    query: str,
    cron_expression: str,
    enable: bool,
    prompt: bool
):
    """Update a topic."""
    try:
        # Find topic
        if topic_id:
            topic = ctx.client.get_topic(UUID(topic_id))
        elif lookup_name:
            topic = ctx.client.find_topic_by_name(lookup_name)
            if not topic:
                raise NotFoundError(f"Topic with name '{lookup_name}' not found")
        else:
            click.echo("[red]Error:[/red] Specify --id or --name to identify topic")
            return

        if prompt:
            # Interactive mode
            update_data, confirmed = prompt_topic_update(
                topic.name,
                topic.query,
                topic.cron_expression,
                topic.is_enabled
            )
            if not confirmed:
                display_warning("Update cancelled")
                return
        else:
            # Flag-based mode
            # Validate cron if provided
            if cron_expression and not validate_cron_expression(cron_expression):
                raise ValidationError(
                    "Invalid cron expression. Expected format: 'minute hour day month weekday'\n"
                    "Example: '0 8 * * *' (daily at 8:00 AM)"
                )

            update_data = TopicUpdate(
                name=new_name,
                query=query,
                cron_expression=cron_expression,
                is_enabled=enable
            )

            # Check if anything to update
            if not any([new_name, query, cron_expression, enable is not None]):
                click.echo("[yellow]No updates specified[/yellow]")
                click.echo("Use -p for interactive mode")
                return

        # Update topic
        result = ctx.client.update_topic(topic.id, update_data)
        display_success(f"Topic updated: {result.name}")

        # Display full details
        if ctx.output_format == "table":
            click.echo()
            display_output(result, format=ctx.output_format)

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@topic.command(name="delete")
@click.option("--id", "topic_id", help="Topic ID")
@click.option("--name", help="Topic name")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
@pass_context
def delete(ctx: Context, topic_id: str, name: str, yes: bool):
    """Delete a topic."""
    try:
        # Find topic
        if topic_id:
            topic = ctx.client.get_topic(UUID(topic_id))
        elif name:
            topic = ctx.client.find_topic_by_name(name)
            if not topic:
                raise NotFoundError(f"Topic with name '{name}' not found")
        else:
            click.echo("[red]Error:[/red] Specify --id or --name")
            return

        # Show topic info
        click.echo(f"Topic: {topic.name}")
        click.echo(f"ID: {topic.id}")
        click.echo(f"Query: {topic.query}")
        click.echo(f"Schedule: {topic.cron_expression}")
        click.echo(f"Subscriptions: {topic.total_subscriptions}")

        # Confirm deletion
        if not yes:
            if not confirm_action(f"Delete topic '{topic.name}'?", default=False):
                display_warning("Deletion cancelled")
                return

        # Delete topic
        ctx.client.delete_topic(topic.id)
        display_success(f"Topic deleted: {topic.name}")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)
