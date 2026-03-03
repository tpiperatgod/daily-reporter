"""User management commands."""

import click
from uuid import UUID
from xndctl.context import pass_context, Context
from xndctl.schemas import UserCreate, UserUpdate
from xndctl.utils import (
    display_paginated_results,
    display_output,
    handle_error,
    confirm_action,
    display_success,
    display_warning,
    console
)
from xndctl.prompts.user import prompt_user_create, prompt_user_update
from xndctl.client import NotFoundError


@click.group(name="user")
def user():
    """Manage users."""
    pass


@user.command(name="create")
@click.option("--name", help="User name")
@click.option("--email", help="User email (required)")
@click.option("--feishu-webhook-url", help="Feishu webhook URL")
@click.option("--feishu-webhook-secret", help="Feishu webhook secret")
@click.option("-p", "--prompt", is_flag=True, help="Interactive mode")
@pass_context
def create(
    ctx: Context,
    name: str,
    email: str,
    feishu_webhook_url: str,
    feishu_webhook_secret: str,
    prompt: bool
):
    """Create a new user."""
    try:
        if prompt:
            # Interactive mode
            user_data, confirmed = prompt_user_create()
            if not confirmed:
                display_warning("User creation cancelled")
                return
        else:
            # Flag-based mode
            if not email:
                console.print("[red]Error:[/red] --email is required")
                click.echo("Use -p for interactive mode")
                return

            user_data = UserCreate(
                name=name,
                email=email,
                feishu_webhook_url=feishu_webhook_url,
                feishu_webhook_secret=feishu_webhook_secret
            )

        # Create user
        result = ctx.client.create_user(user_data)
        display_success(f"User created: {result.email} (ID: {result.id})")

        # Display full details
        if ctx.output_format == "table":
            click.echo()
            display_output(result, format=ctx.output_format)

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@user.command(name="ls")
@click.option("--limit", default=100, help="Number of items to show")
@click.option("--offset", default=0, help="Offset for pagination")
@pass_context
def list_users(ctx: Context, limit: int, offset: int):
    """List all users."""
    try:
        result = ctx.client.list_users(limit=limit, offset=offset)

        # Prepare display columns
        columns = ["id", "name", "email", "created_at"]

        display_paginated_results(
            items=result.items,
            total=result.total,
            limit=result.limit,
            offset=result.offset,
            has_more=result.has_more,
            format=ctx.output_format,
            columns=columns,
            title="Users"
        )

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@user.command(name="get")
@click.option("--id", "user_id", help="User ID")
@click.option("--name", help="User name")
@click.option("--email", help="User email")
@pass_context
def get_user(ctx: Context, user_id: str, name: str, email: str):
    """Get user details."""
    try:
        # Find user by ID, name, or email
        if user_id:
            user = ctx.client.get_user(UUID(user_id))
        elif name:
            user = ctx.client.find_user_by_name(name)
            if not user:
                raise NotFoundError(f"User with name '{name}' not found")
        elif email:
            user = ctx.client.find_user_by_email(email)
            if not user:
                raise NotFoundError(f"User with email '{email}' not found")
        else:
            console.print("[red]Error:[/red] Specify --id, --name, or --email")
            return

        display_output(user, format=ctx.output_format, title="User Details")

        if user.topics and ctx.output_format == "table":
            click.echo()
            console.print(f"[bold]Topics ({len(user.topics)}):[/bold]")
            for topic_id in user.topics:
                click.echo(f"  • {topic_id}")
            click.echo()
            channels = []
            if user.enable_feishu:
                channels.append("feishu")
            if user.enable_email:
                channels.append("email")
            console.print(f"[bold]Channels:[/bold] {', '.join(channels) if channels else 'none'}")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@user.command(name="update")
@click.option("--id", "user_id", help="User ID")
@click.option("--name", "lookup_name", help="User name (for lookup)")
@click.option("--email", "lookup_email", help="User email (for lookup)")
@click.option("--new-name", help="New name")
@click.option("--new-email", help="New email")
@click.option("--feishu-webhook-url", help="Feishu webhook URL")
@click.option("--feishu-webhook-secret", help="Feishu webhook secret")
@click.option("-p", "--prompt", is_flag=True, help="Interactive mode")
@pass_context
def update(
    ctx: Context,
    user_id: str,
    lookup_name: str,
    lookup_email: str,
    new_name: str,
    new_email: str,
    feishu_webhook_url: str,
    feishu_webhook_secret: str,
    prompt: bool
):
    """Update a user."""
    try:
        # Find user
        if user_id:
            user = ctx.client.get_user(UUID(user_id))
        elif lookup_name:
            user = ctx.client.find_user_by_name(lookup_name)
            if not user:
                raise NotFoundError(f"User with name '{lookup_name}' not found")
        elif lookup_email:
            user = ctx.client.find_user_by_email(lookup_email)
            if not user:
                raise NotFoundError(f"User with email '{lookup_email}' not found")
        else:
            console.print("[red]Error:[/red] Specify --id, --name, or --email to identify user")
            return

        if prompt:
            # Interactive mode
            update_data, confirmed = prompt_user_update(user.name, user.email)
            if not confirmed:
                display_warning("Update cancelled")
                return
        else:
            # Flag-based mode
            update_data = UserUpdate(
                name=new_name,
                email=new_email,
                feishu_webhook_url=feishu_webhook_url,
                feishu_webhook_secret=feishu_webhook_secret
            )

            # Check if anything to update
            if not any([new_name, new_email, feishu_webhook_url, feishu_webhook_secret]):
                console.print("[yellow]No updates specified[/yellow]")
                click.echo("Use -p for interactive mode")
                return

        # Update user
        result = ctx.client.update_user(user.id, update_data)
        display_success(f"User updated: {result.email}")

        # Display full details
        if ctx.output_format == "table":
            click.echo()
            display_output(result, format=ctx.output_format)

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


@user.command(name="delete")
@click.option("--id", "user_id", help="User ID")
@click.option("--name", help="User name")
@click.option("--email", help="User email")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
@pass_context
def delete(ctx: Context, user_id: str, name: str, email: str, yes: bool):
    """Delete a user."""
    try:
        # Find user
        if user_id:
            user = ctx.client.get_user(UUID(user_id))
        elif name:
            user = ctx.client.find_user_by_name(name)
            if not user:
                raise NotFoundError(f"User with name '{name}' not found")
        elif email:
            user = ctx.client.find_user_by_email(email)
            if not user:
                raise NotFoundError(f"User with email '{email}' not found")
        else:
            console.print("[red]Error:[/red] Specify --id, --name, or --email")
            return

        # Show user info
        click.echo(f"User: {user.name or '(no name)'} ({user.email})")
        click.echo(f"ID: {user.id}")
        if user.topics:
            click.echo(f"Topics: {len(user.topics)}")

        # Confirm deletion
        if not yes:
            if not confirm_action(f"Delete user '{user.email}'?", default=False):
                display_warning("Deletion cancelled")
                return

        # Delete user
        ctx.client.delete_user(user.id)
        display_success(f"User deleted: {user.email}")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)
