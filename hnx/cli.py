"""Click entrypoint for hnx CLI."""

from __future__ import annotations

import asyncio
import json
import sys

import click

from hnx.algolia_client import AlgoliaClient
from hnx.client import HNClient
from hnx.commands.item import fetch_item_cmd
from hnx.commands.stories import fetch_stories
from hnx.commands.thread import fetch_thread
from hnx.config import Settings
from hnx.errors import HNXError


@click.group()
def cli() -> None:
    """JSON-first HackerNews CLI for agent workflows."""


def _shared_list_options(func):
    """Apply the shared flags (limit / concurrency / ids-only / include-deleted).

    `--limit` and `--concurrency` default to None here and are resolved to
    Settings() values inside `_run_stories` so env vars are read per-invocation
    rather than baked in at module import time.
    """
    func = click.option(
        "--include-deleted",
        is_flag=True,
        default=False,
        help="Include items with deleted:true or dead:true (surfaced as tombstones).",
    )(func)
    func = click.option(
        "--ids-only",
        is_flag=True,
        default=False,
        help="Skip hydration; data is the raw id list.",
    )(func)
    func = click.option(
        "--concurrency",
        type=click.IntRange(min=1),
        default=None,
        help="Concurrent item-hydration requests. [default: HNX_CONCURRENCY or 10]",
    )(func)
    func = click.option(
        "--limit",
        type=click.IntRange(min=1),
        default=None,
        help="Take first N ids from the list and hydrate. [default: HNX_DEFAULT_LIMIT or 30]",
    )(func)
    return func


def _run_stories(
    source: str, limit: int | None, concurrency: int | None, ids_only: bool, include_deleted: bool
) -> None:
    async def _run() -> None:
        settings = Settings()
        effective_limit = limit if limit is not None else settings.default_limit
        effective_concurrency = concurrency if concurrency is not None else settings.concurrency
        async with HNClient(base_url=settings.base_url, concurrency=effective_concurrency) as client:
            envelope = await fetch_stories(
                client=client,
                source=source,
                limit=effective_limit,
                concurrency=effective_concurrency,
                ids_only=ids_only,
                include_deleted=include_deleted,
            )
        click.echo(envelope.model_dump_json())

    try:
        asyncio.run(_run())
    except HNXError as err:
        _handle_error(err)


@cli.command()
@_shared_list_options
def top(limit: int | None, concurrency: int | None, ids_only: bool, include_deleted: bool) -> None:
    """Fetch hydrated top stories."""
    _run_stories("top", limit, concurrency, ids_only, include_deleted)


@cli.command()
@_shared_list_options
def new(limit: int | None, concurrency: int | None, ids_only: bool, include_deleted: bool) -> None:
    """Fetch hydrated new stories."""
    _run_stories("new", limit, concurrency, ids_only, include_deleted)


@cli.command()
@_shared_list_options
def best(limit: int | None, concurrency: int | None, ids_only: bool, include_deleted: bool) -> None:
    """Fetch hydrated best stories."""
    _run_stories("best", limit, concurrency, ids_only, include_deleted)


@cli.command()
@click.argument("item_id", type=int)
@click.option(
    "--include-deleted",
    is_flag=True,
    default=False,
    help="Return deleted/dead items as tombstones instead of erroring.",
)
def item(item_id: int, include_deleted: bool) -> None:
    """Fetch a single item by id."""

    async def _run() -> None:
        settings = Settings()
        async with HNClient(base_url=settings.base_url, concurrency=1) as client:
            envelope = await fetch_item_cmd(client=client, item_id=item_id, include_deleted=include_deleted)
        click.echo(envelope.model_dump_json())

    try:
        asyncio.run(_run())
    except HNXError as err:
        _handle_error(err)


@cli.command()
@click.argument("story_id", type=int)
@click.option("--max-depth", type=click.IntRange(min=1), default=None)
@click.option("--max-comments", type=click.IntRange(min=1), default=None)
@click.option("--raw", "include_raw", is_flag=True, default=False, help="Include raw Algolia payload.")
def thread(story_id: int, max_depth: int | None, max_comments: int | None, include_raw: bool) -> None:
    """Fetch full comment thread for a story."""

    async def _run() -> None:
        settings = Settings()
        async with AlgoliaClient(base_url=settings.algolia_base_url) as client:
            envelope = await fetch_thread(
                client=client,
                story_id=story_id,
                max_depth=max_depth,
                max_comments=max_comments,
                include_raw=include_raw,
            )
        click.echo(envelope.model_dump_json())

    try:
        asyncio.run(_run())
    except HNXError as err:
        _handle_error(err)


def _handle_error(err: HNXError) -> None:
    """Write the structured error envelope to stderr and exit."""
    click.echo(json.dumps(err.to_dict()), err=True)
    sys.exit(err.exit_code)
