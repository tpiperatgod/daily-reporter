from __future__ import annotations

import json
from pathlib import Path


def load_state(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text())


def save_state(path: Path | None, payload: dict) -> None:
    if path is None:
        return
    path.write_text(json.dumps(payload, indent=2) + "\n")
