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
DATE="${DATE:-}"
LAUNCH_LIMIT="${LAUNCH_LIMIT:-30}"
TMP_DIR="${TMP_DIR:-/tmp}"

command -v phx >/dev/null 2>&1 || {
  echo "fetch_launches.sh: phx not found on PATH" >&2
  exit 2
}
command -v jq >/dev/null 2>&1 || {
  echo "fetch_launches.sh: jq not found on PATH" >&2
  exit 2
}

RAW_FILE="${TMP_DIR}/phx_launches_raw_$$.json"

ARGS=(launches --limit "$LAUNCH_LIMIT")
if [ -n "$DATE" ]; then
  ARGS+=(--date "$DATE")
fi

if ! phx "${ARGS[@]}" > "$RAW_FILE"; then
  echo "fetch_launches.sh: phx launches failed" >&2
  exit 3
fi

if ! jq -e '.ok == true and (.data | type == "array") and (.data | length > 0)' "$RAW_FILE" >/dev/null; then
  echo "fetch_launches.sh: phx launches returned no usable launch data" >&2
  exit 3
fi

jq \
  --arg requested_date "$DATE" \
  --argjson launch_limit "$LAUNCH_LIMIT" \
  '{
    ok: true,
    data: {
      launches: .data
    },
    query: {
      command: "ph-daily-report/fetch_launches",
      date: ($requested_date | if . == "" then null else . end),
      resolved_date: .query.date,
      launch_limit: $launch_limit
    },
    meta: {
      launch_count: (.data | length),
      source_meta: .meta,
      fetched_at: (now | todate)
    },
    raw: null
  }' "$RAW_FILE" > "$OUTPUT"

jq -r '"launches ok=\(.ok) date=\(.query.resolved_date) count=\(.meta.launch_count)"' "$OUTPUT" >&2
