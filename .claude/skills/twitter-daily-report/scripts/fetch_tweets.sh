#!/usr/bin/env bash
# Fetch tweets for all 29 seed accounts in parallel using the `twx` CLI.
#
# Usage:
#   SINCE=2026-04-22T00:00:00Z UNTIL=2026-04-23T00:00:00Z \
#     ./fetch_tweets.sh /tmp/twx_raw
#
# Prerequisites:
#   - TWITTER_API_KEY exported (source .env beforehand)
#   - twx CLI on PATH
#
# Output:
#   One JSON file per account at <out_dir>/<username>.json
#   Exit 0 always — the analyzer decides what counts as "no tweets".

set -u

OUT_DIR="${1:-/tmp/twx_raw}"
LIMIT="${LIMIT:-20}"

if [[ -z "${SINCE:-}" || -z "${UNTIL:-}" ]]; then
  RESOLVE_ARGS=(--format shell)
  if [[ -n "${REPORT_DATE:-${DATE:-}}" ]]; then
    RESOLVE_ARGS+=(--date "${REPORT_DATE:-${DATE:-}}")
  fi
  eval "$(python -m drm.report_window "${RESOLVE_ARGS[@]}")"
  SINCE="${SINCE:-$SINCE_UTC}"
  UNTIL="${UNTIL:-$UNTIL_UTC}"
fi

mkdir -p "$OUT_DIR"

# Canonical list of 29 unique accounts (cross-role dedup).
# Keep in sync with docs/tech-twitter-accounts.md.
ACCOUNTS=(
  karpathy AndrewYNg sentdex rasbt dotey lijigang_com ruanyf
  ylecun goodfellow_ian soumithchintala indigo11 karminski3
  esabraha kaifulee levelsio aborroni op7418 AlchainHust
  bourneliu66 _akhaliq aabrazny IntuitMachine WaytoAGI
  Gorden_Sun shao__meng vista8 oran_ge xicilion lifesinger
)

if [[ -z "${TWITTER_API_KEY:-}" ]]; then
  echo "error: TWITTER_API_KEY not set. Run: set -a && source .env && set +a" >&2
  exit 2
fi

echo "fetching ${#ACCOUNTS[@]} accounts into $OUT_DIR (report_date=${REPORT_DATE:-} timezone=${REPORT_TIMEZONE:-} since=$SINCE until=$UNTIL limit=$LIMIT)" >&2

for acct in "${ACCOUNTS[@]}"; do
  twx user \
    --username "$acct" \
    --since "$SINCE" \
    --until "$UNTIL" \
    --limit "$LIMIT" \
    > "$OUT_DIR/${acct}.json" 2>/dev/null &
done
wait

echo "done. files:" >&2
ls -1 "$OUT_DIR"/*.json | wc -l >&2
