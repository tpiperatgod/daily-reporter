#!/usr/bin/env bash
# Fetch a deduped HN candidate pool via `hnx top` + `hnx best` + `hnx new`.
#
# This script does only deterministic work: fetch three lists concurrently,
# merge them, drop duplicates by `id`, and emit a single SuccessEnvelope-shaped
# JSON. All semantic judgment (screening, scoring, selection) happens after.
#
# Usage:
#   fetch_pool.sh [OUTPUT_PATH]
#
# Env overrides:
#   TOP_LIMIT   default 80
#   BEST_LIMIT  default 80
#   NEW_LIMIT   default 60
#   CONCURRENCY default 10   (passed to hnx --concurrency)
#   TMP_DIR     default /tmp (intermediate per-list JSON files go here)
#
# Output envelope:
#   { ok, data: [stories...unique by id], query: {...}, meta: {...}, raw: null }

set -euo pipefail

OUTPUT="${1:-/tmp/hnx_pool.json}"
TOP_LIMIT="${TOP_LIMIT:-80}"
BEST_LIMIT="${BEST_LIMIT:-80}"
NEW_LIMIT="${NEW_LIMIT:-60}"
CONCURRENCY="${CONCURRENCY:-10}"
TMP_DIR="${TMP_DIR:-/tmp}"

RESOLVE_ARGS=(--format shell)
if [ -n "${REPORT_DATE:-${DATE:-}}" ]; then
  RESOLVE_ARGS+=(--date "${REPORT_DATE:-${DATE:-}}")
fi
eval "$(python -m drm.report_window "${RESOLVE_ARGS[@]}")"

command -v hnx >/dev/null 2>&1 || {
  echo "fetch_pool.sh: hnx not found on PATH" >&2
  exit 2
}
command -v jq >/dev/null 2>&1 || {
  echo "fetch_pool.sh: jq not found on PATH" >&2
  exit 2
}

TOP_FILE="${TMP_DIR}/hnx_top.json"
BEST_FILE="${TMP_DIR}/hnx_best.json"
NEW_FILE="${TMP_DIR}/hnx_new.json"

hnx top  --limit "$TOP_LIMIT"  --concurrency "$CONCURRENCY" > "$TOP_FILE"  &
PID_TOP=$!
hnx best --limit "$BEST_LIMIT" --concurrency "$CONCURRENCY" > "$BEST_FILE" &
PID_BEST=$!
hnx new  --limit "$NEW_LIMIT"  --concurrency "$CONCURRENCY" > "$NEW_FILE"  &
PID_NEW=$!

FAILED=0
wait "$PID_TOP"  || { echo "fetch_pool.sh: hnx top failed"  >&2; FAILED=1; }
wait "$PID_BEST" || { echo "fetch_pool.sh: hnx best failed" >&2; FAILED=1; }
wait "$PID_NEW"  || { echo "fetch_pool.sh: hnx new failed"  >&2; FAILED=1; }

if [ "$FAILED" -ne 0 ]; then
  echo "fetch_pool.sh: one or more hnx calls failed; see stderr above" >&2
  exit 3
fi

# Merge + dedupe by id. Keep the first occurrence so `top` wins over `best`,
# `best` wins over `new` (since jq's unique_by keeps the first in input order).
jq -s \
  --argjson top_limit "$TOP_LIMIT" \
  --argjson best_limit "$BEST_LIMIT" \
  --argjson new_limit "$NEW_LIMIT" \
  --arg report_date "$REPORT_DATE" \
  --arg report_timezone "$REPORT_TIMEZONE" \
  --arg date_source "$REPORT_DATE_SOURCE" \
  --arg since_local "$SINCE_LOCAL" \
  --arg until_local "$UNTIL_LOCAL" \
  --arg since_utc "$SINCE_UTC" \
  --arg until_utc "$UNTIL_UTC" '
  ([.[].data[]] | unique_by(.id)) as $all |
  ($all | map(select((.created_at // "") >= $since_utc and (.created_at // "") < $until_utc))) as $filtered |
  {
    ok: (all(.[]; .ok == true)),
    data: $filtered,
    query: {
      command: "hn-daily-report/fetch_pool",
      sources: ["top", "best", "new"],
      limits: {top: $top_limit, best: $best_limit, new: $new_limit},
      report_date: $report_date,
      report_timezone: $report_timezone,
      date_source: $date_source,
      window: {
        since_local: $since_local,
        until_local: $until_local,
        since_utc: $since_utc,
        until_utc: $until_utc
      }
    },
    meta: {
      source_counts: {
        top:  (.[0].data | length),
        best: (.[1].data | length),
        new:  (.[2].data | length)
      },
      candidate_count_before_date_filter: ($all | length),
      filtered_by_report_window: (($all | length) - ($filtered | length)),
      fetched_at: (now | todate)
    },
    raw: null
  }
' "$TOP_FILE" "$BEST_FILE" "$NEW_FILE" > "$OUTPUT"

jq -r '"pool ok=\(.ok) date=\(.query.report_date) total=\(.data | length) top=\(.meta.source_counts.top) best=\(.meta.source_counts.best) new=\(.meta.source_counts.new)"' "$OUTPUT" >&2
