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
jq -s --argjson top_limit "$TOP_LIMIT" --argjson best_limit "$BEST_LIMIT" --argjson new_limit "$NEW_LIMIT" '
  {
    ok: (all(.[]; .ok == true)),
    data: ([.[].data[]] | unique_by(.id)),
    query: {
      command: "hn-daily-report/fetch_pool",
      sources: ["top", "best", "new"],
      limits: {top: $top_limit, best: $best_limit, new: $new_limit}
    },
    meta: {
      source_counts: {
        top:  (.[0].data | length),
        best: (.[1].data | length),
        new:  (.[2].data | length)
      },
      fetched_at: (now | todate)
    },
    raw: null
  }
' "$TOP_FILE" "$BEST_FILE" "$NEW_FILE" > "$OUTPUT"

jq -r '"pool ok=\(.ok) total=\(.data | length) top=\(.meta.source_counts.top) best=\(.meta.source_counts.best) new=\(.meta.source_counts.new)"' "$OUTPUT" >&2
