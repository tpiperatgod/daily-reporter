"""Main CLI entry point for xndctl."""

import sys
import click
from xndctl.config import load_config, init_config, get_config_path
from xndctl.client import APIClient
from xndctl.utils import handle_error


# Context object to pass between commands
class Context:
    """CLI context object."""

    def __init__(self):
        """Initialize context."""
        self.config = None
        self.client = None
        self.verbose = False
        self.output_format = None


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose error output")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["table", "json", "yaml"]),
    help="Output format"
)
@click.pass_context
def cli(click_ctx, verbose: bool, output: str):
    """xndctl - CLI tool for managing X News Digest system.

    Manage users, topics, subscriptions, and trigger data collection.
    """
    # Skip initialization for --help
    if "--help" in sys.argv or not click_ctx.invoked_subcommand:
        if click_ctx.invoked_subcommand is None and "--help" not in sys.argv:
            # No subcommand and no --help, still need config
            pass
        else:
            return

    ctx = click_ctx.ensure_object(Context)
    ctx.verbose = verbose

    try:
        # Load configuration
        config_path = get_config_path()
        if not config_path.exists():
            click.echo("No configuration found. Initializing...")
            ctx.config = init_config(interactive=True)
        else:
            ctx.config = load_config()

        # Override output format if specified
        if output:
            ctx.output_format = output
        else:
            ctx.output_format = ctx.config.output.default_format

        # Initialize API client
        ctx.client = APIClient(ctx.config)

    except Exception as e:
        handle_error(e, verbose=verbose)


@cli.command()
@pass_context
def config(ctx: Context):
    """Show current configuration."""
    config_path = get_config_path()
    click.echo(f"Configuration file: {config_path}")
    click.echo()
    click.echo(f"API Base URL: {ctx.config.api.base_url}")
    click.echo(f"Timeout: {ctx.config.api.timeout}s")
    click.echo(f"Verify SSL: {ctx.config.api.verify_ssl}")
    click.echo(f"Default Output: {ctx.config.output.default_format}")
    click.echo(f"Color Output: {ctx.config.output.color}")
    click.echo(f"Log Level: {ctx.config.logging.level}")


@cli.command()
@click.option("--base-url", help="API base URL")
@pass_context
def init(ctx: Context, base_url: str):
    """Re-initialize configuration."""
    try:
        config = init_config(base_url=base_url, interactive=True)
        click.echo()
        click.echo("[green]✓[/green] Configuration initialized successfully")
    except Exception as e:
        handle_error(e, verbose=ctx.verbose)


# Import command groups
from xndctl.commands import user, topic, subscription, trigger, notify

# Register command groups
cli.add_command(user.user)
cli.add_command(topic.topic)
cli.add_command(subscription.sub)
cli.add_command(trigger.trigger)
cli.add_command(notify.notify)


if __name__ == "__main__":
    cli()
