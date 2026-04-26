---
name: hn-daily-report
description: Generate the daily Hacker News high-value digest for the x-news-digest project using the `hnx` CLI. Use whenever the user asks for the HN daily report, HN digest, Hacker News 日报, HN 高价值内容, HN 今日精选, today's HN roundup, HN 周报, or any variation that involves pulling HN stories + comment threads via `hnx` and producing a judgment-driven report at `docs/reports/hn-daily-YYYY-MM-DD.md`. Also trigger when the user mentions "HN 高价值讨论", "Hacker News 精华", "给我看看 HN 今天最值得读的", "HN thread 分析", "帮我总结 HN 今天的讨论", even without naming the skill. The skill owns the full pipeline: fetching the candidate pool from `top`/`best`/`new`, running a rubric-based semantic screen, pulling full comment trees for high-potential stories, extracting evidence from threads, and writing the final markdown digest with citation links back to each HN story and comment.
---

# HN Daily Report

Generate the daily high-value Hacker News digest. This skill is AI-first by design: the deterministic step (`hnx` fetch + merge) lives in `scripts/`, but every judgment — screening, thread analysis, final selection, writing — is yours. The goal is not to surface trending news, it is to find discussions that change how a practitioner reader would make a technical, product, or architectural decision.

## Core principle

`hnx` only fetches and normalizes. You do all semantic work.

Do not write keyword filters, hard score thresholds, or fixed category rules into scripts. Scores and comment counts are attention signals, not quality signals. A high-score story may be pure news with no decision value; a 40-point story with one veteran engineer's postmortem may be the best thing on the page. Read threads. Cite evidence. Reject items with no practitioner signal — even if they're trending.

Full rationale: [`docs/hnx/hn-digest-sop.md`](../../../docs/hnx/hn-digest-sop.md). Detailed rubric and JSON schemas: [`references/rubric.md`](references/rubric.md).

## Where the ground truth lives

| File | Purpose |
|------|---------|
| `report-template.md` | Markdown template with placeholders (copy into `docs/reports/`) |
| `references/rubric.md` | Story screening rubric + thread analysis JSON schemas |
| `scripts/fetch_pool.sh` | Deterministic pool fetch — runs `hnx top/best/new` in parallel, merges with `jq`, dedupes by `id` |
| `docs/hnx/hn-digest-sop.md` | Full SOP (external, checked in at repo root) — the source of truth for the methodology |

The rubric lives in `references/rubric.md` so SKILL.md stays scannable. Read it when you start Step 2, not upfront.

## Pipeline overview

```
hnx top/best/new ──► fetch_pool.sh ──► /tmp/hnx_pool.json
                                              │
                                              ▼
                              Step 2: AI story screen (rubric)
                                              │
                                              ▼
                       hnx thread <id>  ──► /tmp/hnx_thread_<id>.json
                                              │
                                              ▼
                          Step 4: AI thread analysis (evidence)
                                              │
                                              ▼
         report-template.md + AI prose  ──► docs/reports/hn-daily-YYYY-MM-DD.md
```

The script does one thing: fetch three HN lists concurrently and produce a deduped candidate pool. Everything after that is judgment.

---

## Step-by-step

### Step 0: Define reader and theme

Before fetching, lock in who the report serves. Default reader profile:

- **Audience**: technical founders, AI / infra engineers, independent developers, people making technical product calls.
- **Priority content**: firsthand experience, engineering trade-offs, tool/framework replacements, incident postmortems, regulatory or platform shifts that affect developers, research or product signals that could change a technical choice.
- **Low priority**: release announcements with no discussion, ideological flame wars, news summaries without extra HN insight, "cool but no details" showcases.

If the user specifies a theme ("AI infra", "developer tools", "security", "startups"), use it to bias selection — but never let a theme override the quality bar. A great firsthand-experience thread outside the theme usually beats a mediocre on-theme story.

### Step 1: Fetch the candidate pool

```bash
cd <project root>
eval "$(python -m drm.report_window \
  ${REPORT_DATE:+--date "$REPORT_DATE"} \
  --format shell)"
.claude/skills/hn-daily-report/scripts/fetch_pool.sh /tmp/hnx_pool.json
```

If the user names a specific date, set `REPORT_DATE=YYYY-MM-DD`. Otherwise the shared resolver defaults to yesterday in `Asia/Shanghai`. `fetch_pool.sh` filters hydrated HN items to the shared Beijing report window before writing `/tmp/hnx_pool.json`.

Default pool sizes: `top=80`, `best=80`, `new=60`. Override with env vars if the user asks for a lighter or deeper sweep:

| Scenario | `TOP_LIMIT` | `BEST_LIMIT` | `NEW_LIMIT` | Notes |
|---|---:|---:|---:|---|
| Quick daily | 60 | 40 | 40 | Enough for the day's hot topics |
| Standard daily (default) | 80 | 80 | 60 | — |
| Deep weekly | 120 | 120 | 120 | Surfaces lower-heat but higher-quality items |

```bash
TOP_LIMIT=120 BEST_LIMIT=120 NEW_LIMIT=120 \
  .claude/skills/hn-daily-report/scripts/fetch_pool.sh /tmp/hnx_pool.json
```

Sanity check before moving on:

```bash
jq '{ok, count: (.data | length)}' /tmp/hnx_pool.json
```

If `ok` is not `true` or `count` is unexpectedly small, stop and diagnose (hnx error, network, rate limit) before burning tokens on an empty pool.

### Step 2: AI story screen

Read `/tmp/hnx_pool.json`. For each story, apply the rubric in [`references/rubric.md`](references/rubric.md). The rubric scores six dimensions (`decision_value`, `discussion_potential`, `novelty`, `practitioner_signal`, `transferability`, `audience_fit`) and lists explicit demerits.

Do not keyword-match. The screen is semantic. A story with no obvious tech keywords can still be high-value if the title implies a decision, conflict, or firsthand report; a story with every buzzword in it can be worthless if the discussion is empty.

Output a structured candidate list (schema in `references/rubric.md` under "Story screen output"). Mark the top 5–8 as `thread_priority: high` and fetch their threads next. Always record a `rejected` list with one-line reasons — this becomes the "被拒绝的热门内容" table in the report and also calibrates future runs.

### Step 3: Fetch high-potential threads

For each `thread_priority: high` story:

```bash
hnx thread <story_id> --max-depth 4 --max-comments 80 \
  > /tmp/hnx_thread_<story_id>.json
```

Parameter guidance:

| Scenario | `--max-depth` | `--max-comments` | Use when |
|---|---:|---:|---|
| Quick scan | 3 | 40 | Only need top-level takes + one round of replies |
| Standard (default) | 4 | 80 | Want opinion + counterpoint + side discussions |
| Big debate | 5 | 120 | Story has hundreds of comments with real disagreement |

If `descendants < 10` and the story is not itself a firsthand report, skip the thread fetch — there's nothing to analyze. Record it as rejected ("thin discussion").

You can fetch threads in parallel by backgrounding calls:

```bash
for id in 123 456 789; do
  hnx thread "$id" --max-depth 4 --max-comments 80 \
    > "/tmp/hnx_thread_${id}.json" &
done
wait
```

### Step 4: AI thread analysis

Read each `/tmp/hnx_thread_<id>.json`. Your job is not to summarize every comment — it's to extract the evidence that would change a reader's decision. Full criteria and the output JSON schema are in [`references/rubric.md`](references/rubric.md) under "Thread analysis".

Core check: does the thread contain at least one of —

- Firsthand experience (used, maintained, migrated, shipped, debugged)
- High-quality counterpoint (boundary condition, hidden cost, alternative explanation)
- Transferable engineering lesson
- Multi-angle perspective (dev / user / maintainer / regulator / founder)
- Concrete detail (numbers, versions, architectures, costs, failure modes)

If none of those appear — and the story itself isn't independently important — the verdict is `reject`, no matter the score. Record the reason.

Minimum bar for `include`:
- ≥ 2 independent evidence comments, **or**
- 1 very strong firsthand comment on a story that is itself important, **or**
- Low discussion volume but the topic and source carry clear decision value for the target reader.

Evidence comments must link back to the specific HN comment (`https://news.ycombinator.com/item?id=<comment_id>`). Paraphrase — don't dump long quotes.

### Step 5: Select final items and write the digest

From the `verdict: include` pool, pick 3–5 items. Optimize for **mix**, not for combined score. Recommended composition:

- 1–2 engineering / tooling / methodology
- 1 industry or platform shift
- 1 firsthand experience or incident postmortem
- 0–1 research / AI / security wildcard

Create the report file from the template:

```bash
mkdir -p docs/reports
cp .claude/skills/hn-daily-report/report-template.md "docs/reports/hn-daily-${REPORT_DATE}.md"
```

Then edit `docs/reports/hn-daily-${REPORT_DATE}.md` to fill every placeholder. Per-entry structure is already in the template — keep the section order: 类型 → 原文 → HN 讨论 → HN 信号 → 为什么值得读 → 核心洞察 → 争论脉络 → 实操启发 → 证据 → 注意边界.

Writing rules:

- **Paraphrase, don't quote long blocks.** Link the original comment instead.
- **Never blend external article facts with HN comments.** If a claim comes from the linked article, say so; if it comes from a commenter, cite that comment.
- **Never invent authors, numbers, or quotes.** If you can't trace a claim to a specific story or comment, either delete it or flag it as speculation.
- **Headlines should capture the decision, not the topic.** "Postgres 18 adds X" is a topic. "When Postgres 18's async I/O helps — and when it doesn't" is a decision.
- **Prefer less, better.** 3 strong entries beat 5 weak ones. Do not pad to hit a count.
- **Fill the 被拒绝的热门内容 table** with at least 3 rejected high-attention stories and one-line reasons. This is not filler — it's evidence the screen ran.
- **Fill 数据概览** from the counts you actually produced (pool size, candidate count, threads fetched, included, rejected).

### Step 6: Quality check

Before declaring done, verify:

```bash
REPORT_DATE=<date>
REPORT="docs/reports/hn-daily-${REPORT_DATE}.md"

grep -c "news.ycombinator.com/item" "$REPORT"   # should be ≥ 3 * included + evidence links
grep -n "{.*}" "$REPORT"                         # should return nothing — no leftover placeholders
```

Then eyeball the file:

- Every included entry links both the HN discussion **and** the source URL.
- Every non-trivial claim traces back to a story or a specific comment.
- Score / comment counts appear as background signals only, never as the reason something was included.
- No invented authors, no fabricated quotes, no over-confident extrapolation from thin threads.
- `被拒绝的热门内容` has ≥ 3 rows with real reasons.
- `今日判断` reads as a real thesis about the day, not a list of the entry titles.

### Step 7: Report back

Tell the user:

- Output path (`docs/reports/hn-daily-YYYY-MM-DD.md`)
- Final count (e.g. "4 精选条目, 3 条拒选记录")
- One sentence on the day's theme or tension (e.g. "今天的主线是 AI infra 成本压力和 local-first 工具链的回潮")

Do not paste the full report into chat — it's already on disk.

---

## Common pitfalls

- **Letting score do the judging.** A 600-point story with a shallow comment section is usually a reject. Read the thread, not just the headline.
- **Summarizing comments instead of extracting evidence.** The entry isn't a transcript — it's the decision distilled from the transcript, with links for verification.
- **Mixing article facts and HN commentary.** Readers need to know whether a claim came from the submitted article or from a commenter with stakes in the game.
- **Padding to 5 entries.** If only 3 threads pass the bar, publish 3.
- **Skipping rejected list.** The rejected table is part of the product — it calibrates the reader's trust and the skill's future judgment boundary.
- **Running `hnx new` alone and calling it done.** `new` is noisy and mostly unvetted; it's valuable only in combination with `top`/`best` for low-heat discovery.
- **Interpreting the SOP as rules to hardcode.** The SOP describes the reasoning you apply. Do not turn it into a regex.

## Extending the skill

- **Weekly digest**: widen pool sizes, loosen the Step 1 window, and group final entries by theme rather than a flat list. The scripts don't need to change.
- **Themed digest** (e.g. "HN security weekly"): apply the theme as a bias during Step 2 screening and during final selection in Step 5. Do not filter the pool by keyword before Step 2.
- **New value type**: add a label to `value_type` in `references/rubric.md` and teach it by example in the rubric; do not encode it in a script.
