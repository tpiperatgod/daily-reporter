#!/usr/bin/env bash
# Fetch a Product Hunt launch pool via `phx launches`.
#
# This script does deterministic data collection only. The skill decides which
# launches are worth enriching and which products enter the final report.
#
# Usage:
#   fetch_launches.sh [OUTPUT_PATH]
#
# Env:
#   DATE          optional Product Hunt day, YYYY-MM-DD
#   LAUNCH_LIMIT  default 30
#   TMP_DIR       default /tmp

set -euo pipefail

OUTPUT="${1:-/tmp/phx_launches.json}"
LAUNCH_LIMIT="${LAUNCH_LIMIT:-30}"
TMP_DIR="${TMP_DIR:-/tmp}"

RESOLVE_ARGS=(--format shell)
if [ -n "${REPORT_DATE:-${DATE:-}}" ]; then
  RESOLVE_ARGS+=(--date "${REPORT_DATE:-${DATE:-}}")
fi
eval "$(python -m drm.report_window "${RESOLVE_ARGS[@]}")"

command -v phx >/dev/null 2>&1 || {
  echo "fetch_launches.sh: phx not found on PATH" >&2
  exit 2
}
command -v jq >/dev/null 2>&1 || {
  echo "fetch_launches.sh: jq not found on PATH" >&2
  exit 2
}

RAW_FILE="${TMP_DIR}/phx_launches_raw_$$.json"

ARGS=(launches --limit "$LAUNCH_LIMIT" --after "$SINCE_UTC" --before "$UNTIL_UTC")

if ! phx "${ARGS[@]}" > "$RAW_FILE"; then
  echo "fetch_launches.sh: phx launches failed" >&2
  exit 3
fi

if ! jq -e '.ok == true and (.data | type == "array") and (.data | length > 0)' "$RAW_FILE" >/dev/null; then
  echo "fetch_launches.sh: phx launches returned no usable launch data" >&2
  exit 3
fi

jq \
  --arg report_date "$REPORT_DATE" \
  --arg report_timezone "$REPORT_TIMEZONE" \
  --arg date_source "$REPORT_DATE_SOURCE" \
  --arg since_local "$SINCE_LOCAL" \
  --arg until_local "$UNTIL_LOCAL" \
  --arg since_utc "$SINCE_UTC" \
  --arg until_utc "$UNTIL_UTC" \
  --argjson launch_limit "$LAUNCH_LIMIT" \
  '{
    ok: true,
    data: {
      launches: .data
    },
    query: {
      command: "ph-daily-report/fetch_launches",
      date: $report_date,
      resolved_date: $report_date,
      report_timezone: $report_timezone,
      date_source: $date_source,
      launch_limit: $launch_limit,
      window: {
        since_local: $since_local,
        until_local: $until_local,
        since_utc: $since_utc,
        until_utc: $until_utc
      },
      source_query: .query
    },
    meta: {
      launch_count: (.data | length),
      source_meta: .meta,
      fetched_at: (now | todate)
    },
    raw: null
  }' "$RAW_FILE" > "$OUTPUT"

jq -r '"launches ok=\(.ok) date=\(.query.resolved_date) count=\(.meta.launch_count)"' "$OUTPUT" >&2
