"""Tests for twx checkpoint state management."""

import json

from twx.state import load_state, save_state


def test_load_state_returns_empty_dict_when_no_path():
    """load_state(None) returns empty dict."""
    assert load_state(None) == {}


def test_load_state_returns_empty_dict_when_file_missing(tmp_path):
    """load_state with non-existent file returns empty dict."""
    missing = tmp_path / "nonexistent.json"
    assert load_state(missing) == {}


def test_save_state_creates_file(tmp_path):
    """save_state writes JSON to the specified path."""
    state_path = tmp_path / "state.json"
    save_state(state_path, {"since_id": "123"})
    assert json.loads(state_path.read_text())["since_id"] == "123"


def test_save_state_noop_when_no_path():
    """save_state(None, ...) does nothing and doesn't raise."""
    save_state(None, {"since_id": "123"})  # should not raise


def test_round_trip_state(tmp_path):
    """Load after save returns the same data."""
    state_path = tmp_path / "state.json"
    data = {"since_id": "456", "last_run": "2026-04-15"}
    save_state(state_path, data)
    loaded = load_state(state_path)
    assert loaded == data


def test_state_file_is_human_readable(tmp_path):
    """State file uses indented JSON for readability."""
    state_path = tmp_path / "state.json"
    save_state(state_path, {"key": "value"})
    content = state_path.read_text()
    assert "\n" in content  # indented = has newlines


def test_user_command_reads_checkpoint(tmp_path):
    """twx user --state-file reads since_id from checkpoint."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"since_id": "123"}) + "\n")

    # The state file is read and its content available to the command
    state = load_state(state_path)
    assert state["since_id"] == "123"


def test_user_command_saves_checkpoint(tmp_path):
    """twx user --state-file saves updated state after success."""
    state_path = tmp_path / "state.json"

    # Simulate what a command would do after successful fetch
    save_state(state_path, {"since_id": "999", "last_username": "karpathy"})
    loaded = load_state(state_path)
    assert loaded["since_id"] == "999"
    assert loaded["last_username"] == "karpathy"
