# Time Window Parameter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `--time-window` parameter support to `xndctl trigger` CLI command, allowing users to specify 4h, 12h, or 24h time range for data collection.

**Architecture:** Update CLI to pass time_window query parameter to backend API. Add interactive prompt for time window selection. Display selected time window in output.

**Tech Stack:** Python 3.10+, Click, Rich/console, httpx

---

## Task 1: Update API Client

**Files:**
- Modify: `cli/xndctl/client.py:198-210`

**Step 1: Update trigger_user method signature**

Add `time_window` parameter to the `trigger_user` method in `cli/xndctl/client.py`:

```python
def trigger_user(self, user_id: UUID, time_window: str = "24h") -> UserTriggerResponse:
    """Trigger data collection for all topics subscribed by a user.

    Args:
        user_id: UUID of the user
        time_window: Time window for collection (4h, 12h, 24h, or 1d)

    Returns:
        UserTriggerResponse with task ID and topic count
    """
    with self._get_client() as client:
        response = client.post(
            f"{self.base_url}/api/v1/users/{user_id}/trigger",
            params={"time_window": time_window}
        )
        data = self._handle_response(response)
        return UserTriggerResponse(**data)
```

**Step 2: Verify no syntax errors**

Run: `python -c "from xndctl.client import APIClient; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add cli/xndctl/client.py
git commit -m "feat(cli): add time_window parameter to trigger_user client method"
```

---

## Task 2: Add Time Window Prompt Helper

**Files:**
- Modify: `cli/xndctl/commands/trigger.py:11-28`

**Step 1: Add prompt_time_window function**

Add this function after the imports section (around line 11), before `prompt_select_user`:

```python
def prompt_time_window() -> str:
    """Prompt user to select time window for data collection."""
    click.echo()
    console.print("[bold]Select Time Window:[/bold]")
    click.echo("  1. 4h  - Last 4 hours")
    click.echo("  2. 12h - Last 12 hours")
    click.echo("  3. 24h - Last 24 hours (default)")

    while True:
        try:
            user_input = click.prompt("\nSelect time window (1-3)", type=int, default=3)
            if user_input == 1:
                return "4h"
            elif user_input == 2:
                return "12h"
            elif user_input == 3:
                return "24h"
            console.print("[red]Invalid selection. Choose 1-3[/red]")
        except Exception:
            console.print("[red]Invalid input. Enter a number 1-3[/red]")
```

**Step 2: Verify no syntax errors**

Run: `cd cli && python -c "from xndctl.commands.trigger import prompt_time_window; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add cli/xndctl/commands/trigger.py
git commit -m "feat(cli): add prompt_time_window helper function"
```

---

## Task 3: Update Trigger Command with time_window Option

**Files:**
- Modify: `cli/xndctl/commands/trigger.py:30-33`

**Step 1: Add --time-window option to click decorator**

Update the `@click.command` decorator to include the new option:

```python
@click.command(name="trigger")
@click.option("-p", "--prompt", is_flag=True, required=True, help="Interactive mode (required)")
@click.option(
    "-t", "--time-window",
    type=click.Choice(["4h", "12h", "24h", "1d"], case_sensitive=True),
    default=None,
    help="Time window for data collection (default: 24h)"
)
@pass_context
def trigger(ctx: Context, prompt: bool, time_window: Optional[str]):
```

**Step 2: Add Optional import**

Add `Optional` to the typing imports at the top of the file:

```python
from typing import List, Optional
```

**Step 3: Verify CLI option is recognized**

Run: `cd cli && xndctl trigger --help`
Expected: Output includes `-t, --time-window` option

**Step 4: Commit**

```bash
git add cli/xndctl/commands/trigger.py
git commit -m "feat(cli): add --time-window option to trigger command"
```

---

## Task 4: Integrate time_window into Trigger Flow

**Files:**
- Modify: `cli/xndctl/commands/trigger.py:76-90`

**Step 1: Add time window determination logic**

After the confirmation prompt (around line 78), add time window logic:

```python
        click.echo()
        if not click.confirm("Trigger digest collection for this user?", default=True):
            display_warning("Trigger cancelled")
            return

        # Determine time window
        if time_window is None:
            time_window = prompt_time_window()
        
        # Normalize 1d to 24h
        if time_window == "1d":
            time_window = "24h"

        display_info(f"Triggering digest collection for user: {selected_user.name or selected_user.email}")
        display_info(f"Time window: {time_window}")

        result = ctx.client.trigger_user(selected_user_id, time_window=time_window)
```

**Step 2: Update success output to show time window**

Update the success display section:

```python
        display_success(f"Digest collection triggered for user: {selected_user.name or selected_user.email}")
        console.print(f"[dim]Topics: {result.topic_count}[/dim]")
        console.print(f"[dim]Time Window: {time_window}[/dim]")
        console.print(f"[dim]Task ID: {task_id}[/dim]")
        console.print(f"[dim]User ID: {selected_user_id}[/dim]")
```

**Step 3: Verify CLI still works**

Run: `cd cli && xndctl trigger --help`
Expected: No errors, shows help with new option

**Step 4: Commit**

```bash
git add cli/xndctl/commands/trigger.py
git commit -m "feat(cli): integrate time_window into trigger flow"
```

---

## Task 5: Manual Integration Test

**Files:**
- None (testing only)

**Step 1: Test with flag**

Run: `cd cli && xndctl trigger -p --time-window 4h`
Expected: 
- User selection prompt appears
- No time window prompt (flag overrides)
- Output shows "Time Window: 4h"

**Step 2: Test without flag (interactive)**

Run: `cd cli && xndctl trigger -p`
Expected:
- User selection prompt appears
- Time window prompt appears (select 1, 2, or 3)
- Output shows selected time window

**Step 3: Test with 1d normalization**

Run: `cd cli && xndctl trigger -p --time-window 1d`
Expected:
- Output shows "Time Window: 24h" (1d normalized)

---

## Task 6: Final Commit and Cleanup

**Step 1: Run linter**

Run: `cd cli && ruff check xndctl/`
Expected: No errors

**Step 2: Run formatter check**

Run: `cd cli && ruff format --check xndctl/`
Expected: All files formatted

**Step 3: Final commit (if any formatting changes)**

```bash
git add cli/xndctl/
git commit -m "style: format cli code after time_window feature"
```

---

## Summary

After completing all tasks:
- `xndctl trigger -p` will prompt for time window selection
- `xndctl trigger -p --time-window 4h` will use 4h without prompting
- Output displays the selected time window
- Backend API receives the time_window query parameter

**Files Modified:**
1. `cli/xndctl/client.py` - Added time_window param to trigger_user()
2. `cli/xndctl/commands/trigger.py` - Added option, prompt, and integration
