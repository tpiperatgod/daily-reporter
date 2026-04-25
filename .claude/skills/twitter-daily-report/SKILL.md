---
name: twitter-daily-report
description: Generate the daily Tech Twitter digest for the x-news-digest / twx project. Use whenever the user asks for the Tech Twitter daily report, tech tweet digest, 技术推特日报, tech twitter 日报, today's Tech Twitter roundup, or any variation that involves pulling tweets from the 29 seed accounts encoded in the skill's scripts (optionally documented in `watchlists/`) and producing a report at docs/reports/tw-daily-YYYY-MM-DD.md. Also use when the user mentions "generate today's report", "run the daily digest", "compile the tweet roundup" — even if they don't explicitly name the skill. This skill owns the full pipeline: loading .env, fetching all seed accounts via `twx` in parallel, scoring tweets with ♥ + 2×🔁 + 3×💬, picking headlines, computing stats, and rendering the markdown report.
---

# Twitter Daily Report

Generate the daily Tech Twitter digest. This skill is a repeatable pipeline: the deterministic parts live in `scripts/`, and you (the model) handle the judgment-heavy parts — writing headlines, 2-3 sentence summaries, and background notes.

## Where the ground truth lives

| File | Purpose |
|------|---------|
| `report-template.md` | Markdown template with placeholders (copied into `docs/reports/`) |
| `scripts/fetch_tweets.sh` | Canonical `ACCOUNTS` array — the list of handles to fetch |
| `scripts/analyze.py` | Canonical `ROLES` + `DISPLAY_NAMES` — role membership and pretty names |
| `watchlists/` | Optional human-readable account catalogs (gitignored, personal) |

The 29-account list and role membership live in the two scripts so the pipeline works offline without any watchlist file. If you edit a watchlist under `watchlists/`, mirror the changes into `fetch_tweets.sh` (`ACCOUNTS`) and `analyze.py` (`ROLES`, `DISPLAY_NAMES`) — drift between them is the most likely source of report bugs.

## Pipeline overview

```
.env  ─┐
        ├──► fetch_tweets.sh ──► /tmp/twx_raw/*.json ──► analyze.py ──► analysis.json
SINCE ─┘                                                                    │
UNTIL ─┘                                                                    │
                                                                            ▼
                          template.md  +  model writes prose  ──► docs/reports/tw-daily-YYYY-MM-DD.md
```

The scripts do the mechanical work (parallel fetch, JSON parsing, scoring, ranking, keyword counting, language ratio). You do the creative work (one-line headlines, tight summaries, background that a non-expert would need).

---

## Step-by-step

### 1. Load env + pick the date window

```bash
cd <project root>
set -a && source .env && set +a

DATE="${DATE:-$(date -u -v-1d +%Y-%m-%d)}"   # default: yesterday UTC
SINCE="${DATE}T00:00:00Z"
UNTIL="$(date -u -v+1d -jf '%Y-%m-%d' "$DATE" +%Y-%m-%d)T00:00:00Z"
echo "date=$DATE since=$SINCE until=$UNTIL"
```

If the user names a specific date ("给我 2026-04-22 的日报"), use that as `DATE`. Otherwise default to yesterday (UTC) — today's tweets are incomplete.

Sanity-check the API key before fetching all 29 accounts:

```bash
twx user --username karpathy --limit 1 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('ok') else 'FAIL', d.get('error',''))"
```

If it prints `FAIL`, stop and tell the user to check `TWITTER_API_KEY` in `.env`. Don't burn 28 more calls on a broken key.

### 2. Fetch all accounts in parallel

```bash
SINCE="$SINCE" UNTIL="$UNTIL" \
  .claude/skills/twitter-daily-report/scripts/fetch_tweets.sh /tmp/twx_raw
```

The script spawns 29 background `twx user` calls and `wait`s. ~30 seconds total. Empty accounts are fine — `analyze.py` treats missing-file or no-tweets identically.

### 3. Run the analyzer

```bash
python3 .claude/skills/twitter-daily-report/scripts/analyze.py /tmp/twx_raw \
  > /tmp/twx_analysis.json
```

The output JSON has four top-level keys:

- `headlines` — up to 5 tweets picked by score, deduped by account, RTs suppressed unless score ≥ 50
- `by_role` — ordered list of `{role, emoji, accounts[{account, display_name, tweets[]}]}`
- `stats` — `total_accounts`, `active_accounts`, `total_tweets`, `max_likes_tweet`, `keywords`, `zh_count`, `en_count`
- `navigation` — per-role `{role, count, active}` for the summary table

Read this file. If `total_tweets` is 0, something is wrong (API auth, date window off) — diagnose before continuing.

### 4. Write the report

```bash
mkdir -p docs/reports
cp .claude/skills/twitter-daily-report/report-template.md docs/reports/tw-daily-${DATE}.md
```

Then fill the template by editing that file. You now have:

- **Structured data** from `analysis.json` (exact numbers, tweet IDs, URLs, role mappings).
- **Raw tweet text** to turn into headlines, summaries, and background notes.

#### Writing the headlines (top section)

For each entry in `headlines`:

- **Headline** — one line, ≤ 30 chars, captures the core claim. Not a truncated copy of the tweet.
- **Summary** — 2-3 sentences. Start with what the tweet actually says. Add background only when it's needed for a non-expert:
  - Mentions an obscure project/company → one clause of context.
  - Uses a non-generic technical term → parenthetical definition.
  - References an earlier tweet or event → name the thread briefly.
  - Self-explanatory → skip the background, keep it tight.
- **Metadata line** — use the exact format from the template: `— @{account} [{role}] | ♥ {likes} 🔁 {retweets} 💬 {replies} | [原文]({url})`.

#### Writing the per-role sections

Go through `by_role` in order (tech_educator → ai_researcher → thought_leader → builder → tech_newscaster → practitioner).

For each account block:

- If `tweets` is empty → **skip the entire `### @{account} — {display_name}` block.** Do not render a placeholder. The report should only contain accounts that actually posted on the day.
- If every account under a given role has empty `tweets` → **skip that role's entire `## {emoji} {role}` section too** (header + divider). The daily report shouldn't show empty role sections.
- If tweets exist → render each one with a bold headline, 2-3 sentence summary, and the metrics line. Same judgment rules as headlines, but shorter summaries are fine (1-2 sentences often enough).

The role-count summary in `## 🔗 快速导航` at the bottom still lists all 6 roles (it's a seed-account landscape view, not a daily activity view) — inactive roles just show `当日活跃 = 0`.

**Tone hint**: the whole report is a tech digest — direct, informative, no marketing voice. If a tweet is low-signal (e.g. a one-word reply that somehow gained traction), summarize honestly rather than inventing depth.

#### Filling the stats & nav tables

Read straight from `stats` and `navigation`. Formats:

- `中/英文推文比` → `{zh_count} / {en_count}`
- 高频关键词 → top 3 from `stats.keywords` joined with `, `
- 最热推文 → `@{max_likes_tweet.account}: {your one-line headline} (♥{max_likes_tweet.likes})`

### 5. Quality check

Before reporting done, verify:

```bash
DATE=<date>
REPORT=docs/reports/tw-daily-${DATE}.md
grep -c "https://x.com/" "$REPORT"            # should match total_tweets + headlines (minus dedup)
! grep -q "该账号今日无更新" "$REPORT"         # should be absent — inactive accounts are skipped, not placeholder'd
grep -cE "^### @" "$REPORT"                    # number of rendered account blocks = active_accounts (headlines excluded)
```

Then eyeball the file:

- Only roles with at least one active account are rendered; inactive roles are fully skipped.
- Rendered roles keep the canonical order (tech_educator → ai_researcher → thought_leader → builder → tech_newscaster → practitioner).
- Headlines from ≤ 5 distinct accounts.
- Each tweet link has a valid `tweet_id` (not empty, not `{tweet_id}`).
- Stats table numbers match what's in the body.
- 🔗 快速导航 table still lists all 6 roles regardless of activity.
- No stray template placeholders like `{headline}` left over.

### 6. Report back

Tell the user the output path (`docs/reports/tw-daily-YYYY-MM-DD.md`), the headline count, the active-account count, and one sentence on what the day's theme was. Don't paste the whole report back into chat — that's what the file is for.

---

## Common pitfalls

- **Forgetting to source `.env`** — `twx` does not auto-load it. You'll get 29 failed fetches before you notice.
- **Running on "today"** — today's tweets are still accumulating. Default to yesterday UTC unless the user explicitly asks for today.
- **Retweet contamination** — if a headline candidate is a retweet (`is_retweet: true`), double-check the score threshold; prefer originals.
- **Drift between watchlist and scripts** — if a `watchlists/*.md` catalog changes, update `ACCOUNTS` in `scripts/fetch_tweets.sh` and `ROLES`/`DISPLAY_NAMES` in `scripts/analyze.py` to match.
- **Empty API response for specific accounts** — normal. `@goodfellow_ian`, `@aborroni`, and others post rarely. Mark as "该账号今日无更新" and move on.

## Extending the skill

- **New date range** (e.g. weekly digest) — the fetch script and analyzer are date-agnostic; the template and stats copy would need adjustment.
- **New account** — optionally document in your `watchlists/*.md`, then mirror into `ROLES`, `DISPLAY_NAMES` (`scripts/analyze.py`) and the `ACCOUNTS` array (`scripts/fetch_tweets.sh`).
- **Different scoring** — edit `score_tweet()` in `analyze.py`. The `♥ + 2×🔁 + 3×💬` formula favors discussion over passive likes; change with intent.
