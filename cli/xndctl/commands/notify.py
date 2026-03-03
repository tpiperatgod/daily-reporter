"""Notify digest command."""

import click
from uuid import UUID
from typing import List, Optional
from xndctl.context import pass_context, Context
from xndctl.schemas import DigestWithDetails, UserWithTopics
from xndctl.utils import handle_error, display_success, display_warning, display_info, truncate_text, console


def prompt_select_digest(digests: List[DigestWithDetails]) -> Optional[UUID]:
    click.echo()
    console.print("[bold]Select Digest:[/bold]")
    for i, digest in enumerate(digests, 1):
        headline = "No headline"
        if isinstance(digest.summary_json, dict) and "headline" in digest.summary_json:
            headline = digest.summary_json["headline"]

        topic_name = digest.topic.name if digest.topic else "Unknown"
        time_range = f"{digest.time_window_start.date()} to {digest.time_window_end.date()}"

        click.echo(f"  {i}. [{topic_name}] {truncate_text(headline, 60)}")
        click.echo(f"      Time: {time_range} | Deliveries: {len(digest.deliveries)}")

    while True:
        try:
            digest_input = click.prompt("\nSelect digest (number, 0 to cancel)", type=int)
            if digest_input == 0:
                return None
            if 1 <= digest_input <= len(digests):
                return digests[digest_input - 1].id
            console.print(f"[red]Invalid selection. Choose 0-{len(digests)}[/red]")
        except Exception:
            console.print(f"[red]Invalid input. Enter a number 0-{len(digests)}[/red]")


def prompt_select_user_for_digest(users: List[UserWithTopics], topic_name: str) -> Optional[UUID]:
    click.echo()
    console.print(f"[bold]Select User to notify for topic '{topic_name}':[/bold]")
    for i, user in enumerate(users, 1):
        display_name = user.name or "(no name)"
        channels = []
        if user.enable_feishu:
            channels.append("feishu")
        if user.enable_email:
            channels.append("email")
        channels_str = ", ".join(channels) if channels else "none"
        click.echo(f"  {i}. {display_name} ({user.email}) - channels: {channels_str}")

    while True:
        try:
            user_input = click.prompt("\nSelect user (number, 0 to cancel)", type=int)
            if user_input == 0:
                return None
            if 1 <= user_input <= len(users):
                return users[user_input - 1].id
            console.print(f"[red]Invalid selection. Choose 0-{len(users)}[/red]")
        except Exception:
            console.print(f"[red]Invalid input. Enter a number 0-{len(users)}[/red]")


@click.command(name="notify")
@click.option("-p", "--prompt", is_flag=True, required=True, help="Interactive mode (required)")
@pass_context
def notify(ctx: Context, prompt: bool):
    try:
        digests_result = ctx.client.list_digests(limit=100)

        if not digests_result.items:
            console.print("[red]Error:[/red] No digests found. Trigger topic collection first.")
            return

        display_info(f"Found {len(digests_result.items)} recent digests")

        selected_digest_id = prompt_select_digest(digests_result.items)

        if not selected_digest_id:
            display_warning("Notification cancelled")
            return

        selected_digest = next(d for d in digests_result.items if d.id == selected_digest_id)
        topic_id = selected_digest.topic_id
        topic_name = selected_digest.topic.name if selected_digest.topic else "Unknown"

        all_users = ctx.client.list_users(limit=1000)
        topic_users = []
        for user in all_users.items:
            if user.topics and str(topic_id) in user.topics:
                topic_users.append(user)

        if not topic_users:
            console.print(f"[red]Error:[/red] No users subscribed to topic '{topic_name}'")
            return

        display_info(f"Found {len(topic_users)} user(s) subscribed to this topic")

        selected_user_id = prompt_select_user_for_digest(topic_users, topic_name)

        if not selected_user_id:
            display_warning("Notification cancelled")
            return

        selected_user = next(u for u in topic_users if u.id == selected_user_id)

        display_info(f"Sending digest to {selected_user.email}...")
        result = ctx.client.send_digest(selected_digest_id, selected_user_id)

        display_success("Digest notification sent")
        click.echo()
        console.print("[bold]Delivery Statistics:[/bold]")
        console.print(f"  Total: {result.total_sent}")
        console.print(f"  Successful: [green]{result.successful}[/green]")
        console.print(f"  Failed: [red]{result.failed}[/red]")

        if result.deliveries:
            click.echo()
            console.print("[bold]Deliveries:[/bold]")
            for delivery in result.deliveries:
                status_color = "green" if delivery.status == "success" else "red"
                status_text = f"[{status_color}]{delivery.status}[/{status_color}]"
                console.print(f"  • {delivery.channel}: {status_text}")
                if delivery.error_msg:
                    console.print(f"    Error: {delivery.error_msg}")

    except Exception as e:
        handle_error(e, verbose=ctx.verbose)
