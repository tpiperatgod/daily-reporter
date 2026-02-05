"""Interactive prompts for user operations."""

import click
from xndctl.utils import console
from typing import Optional, Tuple
from xndctl.schemas import UserCreate, UserUpdate


def prompt_user_create() -> Tuple[UserCreate, bool]:
    """Interactive prompt for creating a user.

    Returns:
        Tuple of (UserCreate object, confirmation)
    """
    click.echo()
    console.print("[bold]Create New User[/bold]")
    console.print("[dim]* = required field[/dim]")
    click.echo()

    # Name (optional)
    name = click.prompt(
        "Name",
        default="",
        show_default=False
    )
    if not name:
        name = None

    # Email (required)
    while True:
        email = click.prompt("Email *", type=str)
        if email and "@" in email:
            break
        console.print("[red]Invalid email address[/red]")

    # Feishu webhook URL (optional)
    feishu_webhook_url = click.prompt(
        "Feishu Webhook URL",
        default="",
        show_default=False
    )
    if not feishu_webhook_url:
        feishu_webhook_url = None

    # Feishu webhook secret (optional)
    feishu_webhook_secret = None
    if feishu_webhook_url:
        secret = click.prompt(
            "Feishu Webhook Secret",
            default="",
            show_default=False,
            hide_input=True
        )
        if secret:
            feishu_webhook_secret = secret

    # Create user object
    user = UserCreate(
        name=name,
        email=email,
        feishu_webhook_url=feishu_webhook_url,
        feishu_webhook_secret=feishu_webhook_secret
    )

    # Display summary and confirm
    click.echo()
    console.print("[bold]User Summary:[/bold]")
    click.echo(f"  Name: {name or '(not set)'}")
    click.echo(f"  Email: {email}")
    click.echo(f"  Feishu Webhook: {feishu_webhook_url or '(not set)'}")
    click.echo(f"  Feishu Secret: {'(set)' if feishu_webhook_secret else '(not set)'}")
    click.echo()

    confirmed = click.confirm("Create this user?", default=True)

    return user, confirmed


def prompt_user_update(current_name: Optional[str], current_email: str) -> Tuple[UserUpdate, bool]:
    """Interactive prompt for updating a user.

    Args:
        current_name: Current user name
        current_email: Current user email

    Returns:
        Tuple of (UserUpdate object, confirmation)
    """
    click.echo()
    console.print("[bold]Update User[/bold]")
    console.print("[dim]Press Enter to keep current value[/dim]")
    click.echo()

    # Name
    name_input = click.prompt(
        f"Name",
        default=current_name or "",
        show_default=True
    )
    name = name_input if name_input else None

    # Email
    email_input = click.prompt(
        f"Email",
        default=current_email,
        show_default=True
    )
    email = email_input if email_input != current_email else None

    # Feishu webhook URL
    feishu_webhook_url_input = click.prompt(
        "Feishu Webhook URL",
        default="",
        show_default=False
    )
    feishu_webhook_url = feishu_webhook_url_input if feishu_webhook_url_input else None

    # Feishu webhook secret
    feishu_webhook_secret = None
    if feishu_webhook_url:
        secret = click.prompt(
            "Feishu Webhook Secret (leave empty to keep current)",
            default="",
            show_default=False,
            hide_input=True
        )
        if secret:
            feishu_webhook_secret = secret

    # Create update object (only include changed fields)
    update = UserUpdate(
        name=name,
        email=email,
        feishu_webhook_url=feishu_webhook_url,
        feishu_webhook_secret=feishu_webhook_secret
    )

    # Check if anything changed
    if not any([name, email, feishu_webhook_url, feishu_webhook_secret]):
        console.print("[yellow]No changes specified[/yellow]")
        return update, False

    # Display summary and confirm
    click.echo()
    console.print("[bold]Changes:[/bold]")
    if name:
        click.echo(f"  Name: {name}")
    if email:
        click.echo(f"  Email: {email}")
    if feishu_webhook_url:
        click.echo(f"  Feishu Webhook: {feishu_webhook_url}")
    if feishu_webhook_secret:
        click.echo(f"  Feishu Secret: (updated)")
    click.echo()

    confirmed = click.confirm("Apply these changes?", default=True)

    return update, confirmed
