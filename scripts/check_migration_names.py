#!/usr/bin/env python3
"""
Migration filename governance check.

Validates that all Alembic migration files follow the project naming convention:
    YYYYMMDD_HHMM_<revision>_<slug>.py

Example: 20260201_1938_f771473dec7c_add_feishu_webhook_secret_to_users.py

Exit codes:
    0 - All migrations conform
    1 - One or more migrations violate convention
"""

import re
import sys
from pathlib import Path

# Pattern: YYYYMMDD_HHMM_<hex_revision>_<slug>.py
MIGRATION_PATTERN = re.compile(r"^\d{8}_\d{4}_[a-f0-9]+_.+\.py$")

# Legacy migrations that predate the convention (exempt from validation)
LEGACY_MIGRATIONS = {
    "000101_0001_001_initial_schema.py",
    "000101_0001_002_add_last_tweet_id.py",
    "000101_0001_003_add_user_digest.py",
}


def validate_migrations(versions_dir: Path) -> tuple[bool, list[str]]:
    """
    Check all migration files in the versions directory.

    Returns:
        (is_valid, errors) - True if all valid, list of error messages
    """
    errors = []

    if not versions_dir.exists():
        print(f"Error: Versions directory not found: {versions_dir}")
        return False, [f"Directory not found: {versions_dir}"]

    migration_files = list(versions_dir.glob("*.py"))
    migration_files = [f for f in migration_files if f.name != "__init__.py"]

    if not migration_files:
        print("No migration files found.")
        return True, []

    for migration_file in sorted(migration_files):
        filename = migration_file.name

        if filename in LEGACY_MIGRATIONS:
            print(f"[LEGACY] {filename} (exempt)")
            continue

        if not MIGRATION_PATTERN.match(filename):
            error_msg = f"INVALID: {filename} - must match YYYYMMDD_HHMM_<revision>_<slug>.py"
            errors.append(error_msg)
            print(f"[FAIL] {error_msg}")
        else:
            print(f"[OK] {filename}")

    return len(errors) == 0, errors


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    versions_dir = project_root / "alembic" / "versions"

    print(f"Checking migrations in: {versions_dir}")
    print("-" * 60)

    is_valid, errors = validate_migrations(versions_dir)

    print("-" * 60)

    if is_valid:
        print("\n✓ All migrations conform to naming convention")
        return 0
    else:
        print(f"\n✗ {len(errors)} migration(s) violate naming convention:")
        for error in errors:
            print(f"  - {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
