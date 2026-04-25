"""Click entrypoint for phx CLI."""

from __future__ import annotations

import asyncio
import json
import sys

import click

from phx.client import ProductHuntClient
from phx.commands.launches import fetch_launches
from phx.commands.product import fetch_product
from phx.config import Settings
from phx.errors import PHXError


@click.group()
def cli() -> None:
    """JSON-first Product Hunt CLI for agent workflows."""


@cli.command()
@click.option("--date", default=None, help="Product Hunt day in YYYY-MM-DD, interpreted in America/Los_Angeles.")
@click.option("--after", default=None, help="Timezone-aware ISO 8601 start datetime.")
@click.option("--before", default=None, help="Timezone-aware ISO 8601 end datetime.")
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=None,
    help="Number of launches to fetch. [default: PHX_DEFAULT_LIMIT or 20]",
)
@click.option("--raw", "include_raw", is_flag=True, default=False, help="Include raw Product Hunt GraphQL response.")
def launches(date: str | None, after: str | None, before: str | None, limit: int | None, include_raw: bool) -> None:
    """Fetch Product Hunt launches."""

    async def _run() -> None:
        settings = Settings()
        effective_limit = limit if limit is not None else settings.default_limit
        async with ProductHuntClient(api_key=settings.require_token(), base_url=settings.base_url) as client:
            envelope = await fetch_launches(
                client=client,
                date=date,
                after=after,
                before=before,
                limit=effective_limit,
                include_raw=include_raw,
            )
        click.echo(envelope.model_dump_json())

    try:
        asyncio.run(_run())
    except PHXError as err:
        _handle_error(err)


@cli.command()
@click.argument("ref")
@click.option("--id", "force_id", is_flag=True, default=False, help="Treat ref as a Product Hunt GraphQL id.")
@click.option("--slug", "force_slug", is_flag=True, default=False, help="Treat ref as a Product Hunt slug.")
@click.option("--raw", "include_raw", is_flag=True, default=False, help="Include raw Product Hunt GraphQL response.")
def product(ref: str, force_id: bool, force_slug: bool, include_raw: bool) -> None:
    """Fetch one Product Hunt product by slug or id."""

    async def _run() -> None:
        settings = Settings()
        async with ProductHuntClient(api_key=settings.require_token(), base_url=settings.base_url) as client:
            envelope = await fetch_product(
                client=client,
                ref=ref,
                force_id=force_id,
                force_slug=force_slug,
                include_raw=include_raw,
            )
        click.echo(envelope.model_dump_json())

    try:
        asyncio.run(_run())
    except PHXError as err:
        _handle_error(err)


def _handle_error(err: PHXError) -> None:
    click.echo(json.dumps(err.to_dict()), err=True)
    sys.exit(err.exit_code)
