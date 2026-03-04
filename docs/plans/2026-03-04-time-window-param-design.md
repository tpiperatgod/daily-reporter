# Design: Add `time_window` Parameter to `xndctl trigger`

**Date**: 2026-03-04
**Status**: Approved
**Author**: Claude (Sisyphus)

## Summary

Add support for `time_window` parameter to the `xndctl trigger` CLI command, allowing users to specify the time range for data collection (4h, 12h, 24h). The backend API already supports this parameter; we need to expose it through the CLI.

## Background

The backend API endpoint `POST /api/v1/users/{user_id}/trigger` accepts a `time_window` query parameter with values `4h`, `12h`, `24h`, or `1d` (alias for 24h). The CLI currently does not expose this parameter, always using the default `24h`.

## Goals

1. Allow users to specify time window via `--time-window` flag
2. Provide interactive prompt for time window selection when using `-p` mode
3. Display selected time window in output

## Non-Goals

- Changing backend behavior (already supports time_window)
- Adding time_window to other commands (only `trigger`)

## Design

### Approach

**Flag + Optional Prompt**: Add `--time-window` flag that can override the interactive prompt. This matches existing CLI patterns where flags can skip prompts.

### CLI Usage

```bash
# Interactive mode with prompt
xndctl trigger -p
# Prompts: Select time window (1-3) [default: 24h]

# Flag overrides prompt
xndctl trigger -p --time-window 4h

# Flag only (future: non-interactive mode)
xndctl trigger --user-id <uuid> --time-window 12h
```

### Implementation Details

#### 1. CLI Changes (`cli/xndctl/commands/trigger.py`)

**Add new Click option:**
```python
@click.option("-t", "--time-window", 
              type=click.Choice(["4h", "12h", "24h", "1d"]), 
              default=None,
              help="Time window for data collection (default: 24h)")
```

**Add prompt helper function:**
```python
def prompt_time_window() -> str:
    """Prompt user to select time window."""
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

**Update trigger function flow:**
```python
def trigger(ctx: Context, prompt: bool, time_window: Optional[str]):
    # ... existing user selection logic ...
    
    # Determine time window
    if time_window is None:
        time_window = prompt_time_window()
    
    # Normalize 1d -> 24h
    if time_window == "1d":
        time_window = "24h"
    
    # Call API with time_window
    result = ctx.client.trigger_user(selected_user_id, time_window=time_window)
    
    # Display with time window info
    display_success(f"Digest collection triggered for user: {selected_user.name or selected_user.email}")
    console.print(f"[dim]Topics: {result.topic_count}[/dim]")
    console.print(f"[dim]Time Window: {time_window}[/dim]")
    console.print(f"[dim]Task ID: {task_id}[/dim]")
```

#### 2. Client Changes (`cli/xndctl/client.py`)

**Update `trigger_user` method:**
```python
def trigger_user(self, user_id: UUID, time_window: str = "24h") -> UserTriggerResponse:
    """Trigger data collection for all topics subscribed by a user.

    Args:
        user_id: UUID of the user
        time_window: Time window for collection (4h, 12h, 24h)

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

#### 3. Output Display

Success message now includes time window:
```
✓ Digest collection triggered for user: John Doe
  Topics: 3
  Time Window: 4h
  Task ID: abc-123-def-456
  User ID: uuid-here
```

### Validation

| Layer | Validation |
|-------|------------|
| CLI | `click.Choice(["4h", "12h", "24h", "1d"])` |
| Backend | Regex pattern `^(4h\|12h\|24h\|1d)$` |

Both layers normalize `1d` to `24h`.

## Files to Modify

1. `cli/xndctl/commands/trigger.py` - Add option, prompt, and update flow
2. `cli/xndctl/client.py` - Update `trigger_user` to pass `time_window` param

## Testing

1. **Manual testing**:
   - `xndctl trigger -p` → verify prompt appears
   - `xndctl trigger -p --time-window 4h` → verify no prompt, uses 4h
   - Verify output shows correct time window

2. **Edge cases**:
   - Invalid time window value (caught by Click)
   - `1d` normalization to `24h`

## Risks

- **Low risk**: Changes are minimal and isolated to CLI layer
- **Backward compatible**: Default behavior unchanged (24h)

## Timeline

Estimated implementation: 15-30 minutes
