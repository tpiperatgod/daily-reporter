#!/usr/bin/env bash
# Fetch Product Hunt product details for slugs selected by the skill.
#
# This script validates and enriches selected slugs. It must not decide which
# products are valuable or which products enter the final report.
#
# Usage:
#   LAUNCHES=/tmp/phx_launches.json SLUGS_FILE=/tmp/slugs.txt fetch_details.sh [OUTPUT_PATH]
#
# Env:
#   LAUNCHES    launch pool JSON path, default /tmp/phx_launches.json
#   SLUGS       comma-separated selected slugs
#   SLUGS_FILE  newline-delimited selected slugs
#   TMP_DIR     default /tmp

set -euo pipefail
shopt -s nullglob

OUTPUT="${1:-/tmp/phx_pool.json}"
LAUNCHES="${LAUNCHES:-/tmp/phx_launches.json}"
SLUGS="${SLUGS:-}"
SLUGS_FILE="${SLUGS_FILE:-}"
TMP_DIR="${TMP_DIR:-/tmp}"

command -v phx >/dev/null 2>&1 || {
  echo "fetch_details.sh: phx not found on PATH" >&2
  exit 2
}
command -v jq >/dev/null 2>&1 || {
  echo "fetch_details.sh: jq not found on PATH" >&2
  exit 2
}

if [ ! -f "$LAUNCHES" ]; then
  echo "fetch_details.sh: launch pool not found: $LAUNCHES" >&2
  exit 2
fi

if ! jq -e '.ok == true and (.data.launches | type == "array") and (.data.launches | length > 0)' "$LAUNCHES" >/dev/null; then
  echo "fetch_details.sh: launch pool has no usable data.launches" >&2
  exit 3
fi

raw_slugs=()
if [ -n "$SLUGS_FILE" ]; then
  if [ ! -f "$SLUGS_FILE" ]; then
    echo "fetch_details.sh: SLUGS_FILE not found: $SLUGS_FILE" >&2
    exit 2
  fi
  while IFS= read -r line || [ -n "$line" ]; do
    [ -z "$line" ] && continue
    raw_slugs+=("$line")
  done < "$SLUGS_FILE"
elif [ -n "$SLUGS" ]; then
  IFS=',' read -r -a raw_slugs <<< "$SLUGS"
else
  echo "fetch_details.sh: provide SLUGS or SLUGS_FILE" >&2
  exit 2
fi

unique_slugs=()
for slug in "${raw_slugs[@]}"; do
  slug="$(printf '%s' "$slug" | xargs)"
  [ -z "$slug" ] && continue
  already_seen=0
  for existing in "${unique_slugs[@]:-}"; do
    if [ "$existing" = "$slug" ]; then
      already_seen=1
      break
    fi
  done
  if [ "$already_seen" -eq 0 ]; then
    unique_slugs+=("$slug")
  fi
done

if [ "${#unique_slugs[@]}" -lt 1 ] || [ "${#unique_slugs[@]}" -gt 15 ]; then
  echo "fetch_details.sh: expected 1-15 unique slugs, got ${#unique_slugs[@]}" >&2
  exit 2
fi

for slug in "${unique_slugs[@]}"; do
  if ! jq -e --arg slug "$slug" '.data.launches[]? | select(.slug == $slug)' "$LAUNCHES" >/dev/null; then
    echo "fetch_details.sh: slug not present in launch pool: $slug" >&2
    exit 2
  fi
done

WORK_DIR="$(mktemp -d "${TMP_DIR%/}/phx_details.XXXXXX")"
pids=()

for slug in "${unique_slugs[@]}"; do
  (
    detail_file="${WORK_DIR}/detail_${slug}.json"
    error_file="${WORK_DIR}/error_${slug}.json"
    stderr_file="${WORK_DIR}/stderr_${slug}.txt"

    if phx product "$slug" > "$detail_file" 2> "$stderr_file" \
      && jq -e '.ok == true and (.data | type == "object")' "$detail_file" >/dev/null; then
      exit 0
    fi

    jq -n \
      --arg slug "$slug" \
      --rawfile stderr "$stderr_file" \
      --slurpfile payload "$detail_file" \
      '{
        slug: $slug,
        stderr: $stderr,
        payload: ($payload[0] // null)
    }' > "$error_file"
    rm -f "$detail_file"
  ) &
  pids+=("$!")
done

FAILED=0
for pid in "${pids[@]}"; do
  wait "$pid" || FAILED=1
done

if [ "$FAILED" -ne 0 ]; then
  echo "fetch_details.sh: one or more detail workers failed unexpectedly" >&2
  exit 3
fi

detail_files=("${WORK_DIR}"/detail_*.json)
error_files=("${WORK_DIR}"/error_*.json)
DETAILS_JSON="${WORK_DIR}/details.json"
ERRORS_JSON="${WORK_DIR}/errors.json"

if [ "${#detail_files[@]}" -gt 0 ]; then
  jq -s '[.[].data]' "${detail_files[@]}" > "$DETAILS_JSON"
else
  printf '[]\n' > "$DETAILS_JSON"
fi

if [ "${#error_files[@]}" -gt 0 ]; then
  jq -s '.' "${error_files[@]}" > "$ERRORS_JSON"
else
  printf '[]\n' > "$ERRORS_JSON"
fi

SLUGS_JSON="$(printf '%s\n' "${unique_slugs[@]}" | jq -R . | jq -s .)"

jq \
  --argjson detail_slugs "$SLUGS_JSON" \
  --slurpfile details "$DETAILS_JSON" \
  --slurpfile detail_errors "$ERRORS_JSON" \
  '{
    ok: true,
    data: {
      launches: .data.launches,
      details: $details[0],
      detail_errors: $detail_errors[0]
    },
    query: {
      command: "ph-daily-report/fetch_details",
      date: .query.date,
      resolved_date: .query.resolved_date,
      report_timezone: .query.report_timezone,
      date_source: .query.date_source,
      window: .query.window,
      launch_limit: .query.launch_limit,
      detail_slugs: $detail_slugs
    },
    meta: {
      launch_count: (.data.launches | length),
      detail_count: ($details[0] | length),
      detail_error_count: ($detail_errors[0] | length),
      fetched_at: (now | todate)
    },
    raw: null
  }' "$LAUNCHES" > "$OUTPUT"

jq -r '"details ok=\(.ok) date=\(.query.resolved_date) details=\(.meta.detail_count) errors=\(.meta.detail_error_count)"' "$OUTPUT" >&2
