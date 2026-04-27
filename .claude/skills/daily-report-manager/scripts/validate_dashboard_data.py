#!/usr/bin/env python3
"""Validate daily-report-manager dashboard-data JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from drm.dashboard_data import load_dashboard_data, validate_dashboard_data
from drm.errors import DRMError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--inventory", type=Path)
    args = parser.parse_args(argv)

    try:
        data = load_dashboard_data(args.input)
        inventory = None
        if args.inventory:
            inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        validate_dashboard_data(data, inventory=inventory)
    except (DRMError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"valid dashboard data: {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
