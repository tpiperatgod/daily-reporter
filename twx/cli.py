"""Click entrypoint for twx CLI."""

import json
import sys
from pathlib import Path

import click

from twx.errors import TWXError


@click.group()
def cli() -> None:
    """Agent-first Twitter/X CLI."""


@cli.command()
@click.option("--username", required=True, help="Twitter username to fetch tweets from")
@click.option("--limit", type=int, default=20, help="Maximum tweets to return")
@click.option("--since", default=None, help="Only tweets after this ISO timestamp")
@click.option("--until", default=None, help="Only tweets before this ISO timestamp")
@click.option("--include-replies", is_flag=True, default=False, help="Include replies")
@click.option("--state-file", default=None, type=click.Path(), help="Checkpoint state file path")
@click.option("--raw", is_flag=True, default=False, help="Include raw upstream payload")
def user(
    username: str,
    limit: int,
    since: str | None,
    until: str | None,
    include_replies: bool,
    state_file: str | None,
    raw: bool,
) -> None:
    """Fetch tweets from a user timeline."""
    try:
        from twx.client import TwitterApiClient
        from twx.commands.user import fetch_user_tweets
        from twx.config import Settings

        settings = Settings()
        api_key = settings.require_api_key()
        client = TwitterApiClient(api_key=api_key, base_url=settings.base_url)
        state_path = Path(state_file) if state_file else None
        envelope = fetch_user_tweets(
            client=client,
            username=username,
            since=since,
            until=until,
            limit=limit,
            include_replies=include_replies,
            include_raw=raw,
            state_path=state_path,
        )
        click.echo(envelope.model_dump_json())
    except TWXError:
        raise
    except Exception as exc:
        raise TWXError(str(exc)) from exc


@cli.command()
@click.option("--query", required=True, help="Search query string")
@click.option("--mode", type=click.Choice(["latest", "top"]), default="latest", help="Search mode")
@click.option("--limit", type=int, default=20, help="Maximum tweets to return")
@click.option("--state-file", default=None, type=click.Path(), help="Checkpoint state file path")
@click.option("--raw", is_flag=True, default=False, help="Include raw upstream payload")
def search(query: str, mode: str, limit: int, state_file: str | None, raw: bool) -> None:
    """Search tweets by query."""
    try:
        from twx.client import TwitterApiClient
        from twx.commands.search import fetch_search_tweets
        from twx.config import Settings

        settings = Settings()
        api_key = settings.require_api_key()
        client = TwitterApiClient(api_key=api_key, base_url=settings.base_url)
        state_path = Path(state_file) if state_file else None
        envelope = fetch_search_tweets(
            client=client,
            query=query,
            mode=mode,
            limit=limit,
            include_raw=raw,
            state_path=state_path,
        )
        click.echo(envelope.model_dump_json())
    except TWXError:
        raise
    except Exception as exc:
        raise TWXError(str(exc)) from exc


@cli.command()
@click.option("--ranking", type=click.Choice(["upstream", "engagement"]), default="upstream", help="Ranking mode")
@click.option("--limit", type=int, default=20, help="Maximum tweets to return")
@click.option("--state-file", default=None, type=click.Path(), help="Checkpoint state file path")
@click.option("--raw", is_flag=True, default=False, help="Include raw upstream payload")
def trending(ranking: str, limit: int, state_file: str | None, raw: bool) -> None:
    """Fetch trending tweets."""
    try:
        from twx.client import TwitterApiClient
        from twx.commands.trending import fetch_trending_tweets
        from twx.config import Settings

        settings = Settings()
        api_key = settings.require_api_key()
        client = TwitterApiClient(api_key=api_key, base_url=settings.base_url)
        state_path = Path(state_file) if state_file else None
        envelope = fetch_trending_tweets(
            client=client,
            ranking=ranking,
            limit=limit,
            include_raw=raw,
            state_path=state_path,
        )
        click.echo(envelope.model_dump_json())
    except TWXError:
        raise
    except Exception as exc:
        raise TWXError(str(exc)) from exc


def _handle_error(error: TWXError) -> None:
    """Write structured JSON error to stderr and exit."""
    payload = error.to_dict()
    click.echo(json.dumps(payload, indent=2), err=True)
    sys.exit(error.exit_code)
