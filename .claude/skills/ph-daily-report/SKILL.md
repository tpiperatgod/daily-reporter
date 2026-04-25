---
name: ph-daily-report
description: >-
  Generate the daily Product Hunt report for the x-news-digest project using
  the `phx` CLI. Use whenever the user asks for a Product Hunt daily report,
  PH daily report, Product Hunt 日报, PH 今日新品, Product Hunt 今日精选,
  Product Hunt Daily Scout, or any variation that involves pulling Product Hunt
  launches via `phx` and producing a value-judgment report at
  `docs/reports/ph-daily-YYYY-MM-DD.md`. Also use when the user asks
  "给我今天 Product Hunt 值得看的产品", "run the Product Hunt digest", or
  mentions using `phx` for a daily Product Hunt report. The skill owns the
  full pipeline — loading `.env`, fetching launches, shallow-screening 10-15
  products for detail fetch, applying a rubric, selecting 3-5 deep picks,
  recording rejected hot products, and writing the markdown report.
---

# Product Hunt Daily Report

Generate the daily Product Hunt scout report. `phx` only fetches and normalizes Product Hunt data; you judge product value and write the report.

## Core Principle

Do not let rank, votes, comments, or script order decide the final report. They are attention signals. Your job is to decide which products matter for AI practitioners, developers, independent builders, and startup operators.

Do not hardcode keyword filters or fixed score thresholds. Read the launch metadata, choose detail candidates, fetch details, then make final selections.

Read [`references/rubric.md`](references/rubric.md) before shallow screening.

## Ground Truth Files

| File | Purpose |
|---|---|
| `report-template.md` | Markdown template copied into `docs/reports/` |
| `references/rubric.md` | Screening and final-selection rubric |
| `scripts/fetch_launches.sh` | Deterministic `phx launches` wrapper |
| `scripts/fetch_details.sh` | Deterministic detail fetcher for agent-selected slugs |

## Pipeline

```text
.env / PRODUCTHUNT_TOKEN
        |
        v
fetch_launches.sh -> /tmp/phx_launches.json
        |
        v
AI shallow screen -> /tmp/phx_detail_slugs.txt
        |
        v
fetch_details.sh -> /tmp/phx_pool.json
        |
        v
AI final judgment + report-template.md
        |
        v
docs/reports/ph-daily-YYYY-MM-DD.md
```

## Step-by-step

### 1. Load env and sanity-check `phx`

```bash
cd <project root>
if [ -f .env ]; then
  set -a && source .env && set +a
fi

phx launches --limit 1 >/tmp/phx_check.json
```

If this fails, stop and report the `phx` / `PRODUCTHUNT_TOKEN` problem. Do not write an empty report.

### 2. Fetch launch pool

If the user specified a date, set `DATE=YYYY-MM-DD`. Otherwise leave `DATE` unset so `phx` resolves the current Product Hunt day in `America/Los_Angeles`.

```bash
LAUNCH_LIMIT="${LAUNCH_LIMIT:-30}" \
  .claude/skills/ph-daily-report/scripts/fetch_launches.sh /tmp/phx_launches.json
```

Sanity check:

```bash
jq '{ok, resolved_date: .query.resolved_date, launches: (.data.launches | length)}' /tmp/phx_launches.json
```

If `ok` is not `true` or `launches` is `0`, stop and diagnose.

### 3. Shallow-screen detail candidates

Read `/tmp/phx_launches.json` and `references/rubric.md`.

Select `10-15` slugs for detail fetch. Use rank, votes, comments, topics, tagline, description, maker names, and audience fit as provisional signals. Do not select only the top-ranked products.

Write one slug per line:

```bash
cat >/tmp/phx_detail_slugs.txt <<'EOF'
slug-one
slug-two
EOF
```

Also keep a short working note for yourself with the provisional reason for each selected slug. These reasons are audit trail, not final recommendations.

### 4. Fetch details for selected slugs

```bash
LAUNCHES=/tmp/phx_launches.json SLUGS_FILE=/tmp/phx_detail_slugs.txt \
  .claude/skills/ph-daily-report/scripts/fetch_details.sh /tmp/phx_pool.json
```

Sanity check:

```bash
jq '{ok, resolved_date: .query.resolved_date, launches: .meta.launch_count, details: .meta.detail_count, detail_errors: .meta.detail_error_count}' /tmp/phx_pool.json
```

If fewer than `5` details succeeded under default settings, stop. The evidence is too thin for a daily report.

### 5. Final screen and write report

Read `/tmp/phx_pool.json`. Re-evaluate every enriched product using the rubric. Pick `3-5` deep selections. Prefer `3` strong picks over padding to `5`.

Also record `3-5` high-attention rejected products. A rejected product can come from the enriched detail pool or the launch pool, but the reason must be a value judgment, not "rank too low".

Create the report:

```bash
RESOLVED_DATE="$(jq -r '.query.resolved_date' /tmp/phx_pool.json)"
mkdir -p docs/reports
cp .claude/skills/ph-daily-report/report-template.md "docs/reports/ph-daily-${RESOLVED_DATE}.md"
```

Fill every placeholder. Product names, taglines, topics, makers, and source fields stay in English. Analysis and judgment are in Chinese.

### 6. Quality check

```bash
REPORT="docs/reports/ph-daily-${RESOLVED_DATE}.md"

if grep -n "{.*}" "$REPORT"; then
  echo "placeholder(s) remain in $REPORT" >&2
  exit 1
fi

grep -c "producthunt.com" "$REPORT"
grep -c "## 深度精选" "$REPORT"
grep -c "## 被拒绝的热门产品" "$REPORT"
```

Then inspect the report:

- 3-5 deep picks are present.
- Top-list overview has 10 rows unless the launch pool has fewer launches.
- Rejected hot-products table has at least 3 rows.
- Every deep pick includes Product Hunt link, PH signal, topics, and website when source data has one.
- No final inclusion reason is only rank, votes, or comments.
- No invented competitors, funding, users, pricing, maker background, or traction.
- Inferences from Product Hunt metadata are labeled as inference.

### 7. Report back

Tell the user:

- Output path: `docs/reports/ph-daily-YYYY-MM-DD.md`
- Final count: e.g. `4 精选条目, 3 条拒选记录`
- One sentence on the day's main product/market theme.

Do not paste the full report into chat.

## Common Pitfalls

- Fetching details for top-ranked products automatically. The skill must choose detail slugs.
- Treating Product Hunt heat as product quality.
- Translating taglines into inaccurate Chinese slogans.
- Inventing facts from outside Product Hunt data.
- Padding the deep picks when only three products are strong.
- Omitting rejected products; the rejected table calibrates judgment.
