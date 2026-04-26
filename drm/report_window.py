"""Shared report-date window resolver for daily report scripts."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE = "Asia/Shanghai"


def parse_now(value: str, *, report_timezone: ZoneInfo) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"--now must be ISO 8601: {value!r}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=report_timezone)
    return parsed.astimezone(report_timezone)


def resolve_window(*, date: str | None, now: str | None, timezone_name: str) -> dict[str, str]:
    try:
        report_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {timezone_name}") from exc

    if date is None:
        reference = parse_now(now, report_timezone=report_timezone) if now else datetime.now(report_timezone)
        report_day = reference.date() - timedelta(days=1)
        date_source = "default_yesterday"
    else:
        try:
            report_day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"--date must be YYYY-MM-DD: {date!r}") from exc
        date_source = "explicit"

    since_local = datetime(report_day.year, report_day.month, report_day.day, tzinfo=report_timezone)
    until_local = since_local + timedelta(days=1)
    since_utc = since_local.astimezone(timezone.utc)
    until_utc = until_local.astimezone(timezone.utc)

    return {
        "report_date": report_day.isoformat(),
        "report_timezone": timezone_name,
        "date_source": date_source,
        "since_local": since_local.isoformat(),
        "until_local": until_local.isoformat(),
        "since_utc": since_utc.isoformat(),
        "until_utc": until_utc.isoformat(),
    }


def emit_shell(doc: dict[str, str]) -> str:
    mapping = {
        "REPORT_DATE": doc["report_date"],
        "REPORT_TIMEZONE": doc["report_timezone"],
        "REPORT_DATE_SOURCE": doc["date_source"],
        "SINCE_LOCAL": doc["since_local"],
        "UNTIL_LOCAL": doc["until_local"],
        "SINCE_UTC": doc["since_utc"],
        "UNTIL_UTC": doc["until_utc"],
    }
    return "\n".join(f"{key}={shlex.quote(value)}" for key, value in mapping.items())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Explicit report date in YYYY-MM-DD.")
    parser.add_argument("--now", help="Reference timestamp for default date resolution; mostly for tests.")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help=f"Report timezone. Default: {DEFAULT_TIMEZONE}.")
    parser.add_argument("--format", choices=("json", "shell"), default="json")
    args = parser.parse_args(argv)

    try:
        doc = resolve_window(date=args.date, now=args.now, timezone_name=args.timezone)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.format == "shell":
        print(emit_shell(doc))
    else:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
