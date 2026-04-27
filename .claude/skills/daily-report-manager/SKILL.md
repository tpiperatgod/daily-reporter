---
name: daily-report-manager
description: Curate existing Twitter, Hacker News, and Product Hunt daily Markdown reports into the static Daily Report Manager dashboard for x-news-digest. Use whenever the user asks to update, rebuild, refresh, browse, generate, or curate the daily report dashboard, 日报看板, 日报管理, drm dashboard, daily report manager, or "把日报整理成 dashboard". This skill consumes docs/reports/*.md, writes docs/dashboard/dashboard-data.json, validates it against the schema, and calls `drm dashboard build`. It does not call upstream APIs and does not generate the source daily reports.
---

# Daily Report Manager

Build the dashboard from existing reports under `docs/reports/`. Do not fetch upstream APIs and do not generate the source daily reports here — those are owned by the per-source skills (`twitter-daily-report`, `hn-daily-report`, `ph-daily-report`).

The `drm` CLI is the deterministic renderer. This skill owns the AI judgment that decides what content appears in the dashboard.

## Workflow

1. **Inventory the reports.** Run the deterministic scanner so you have authoritative paths, line numbers, and canonical anchors. Do not invent these by hand.

   ```bash
   python .claude/skills/daily-report-manager/scripts/inventory_reports.py \
     --reports-dir docs/reports \
     --output /tmp/drm-report-inventory.json
   ```

2. **Read the inventory and the relevant Markdown.** Open `/tmp/drm-report-inventory.json`, then read the source `docs/reports/*.md` files for any date you intend to curate. Use the inventory to find headings and `line_start` values — copy them, don't rewrite them.

3. **Read the schema reference.** Before writing JSON, read `references/dashboard-schema.md`. It contains the field shapes, status rules, and size limits the validator enforces.

4. **Ask the user for the per-source block limit.** Before curating, use the `question` tool to ask:

   > "Each source (`twitter`, `hackernews`, `producthunt`) is curated **independently** and can have up to 15 selected blocks. With all 3 sources available, that means up to **45 blocks per date** (15 × 3), not 15 total. How many blocks **per source** do you want for this run?"

   Options to present:
   - "15 per source" — maximum signal, content-rich days (up to 45 blocks/date)
   - "10 per source" — balanced (up to 30 blocks/date)
   - "5 per source" — concise (up to 15 blocks/date)

   If the user picks the first option or does not answer, set `max_blocks = 15`. Store this value for the next step.

   `max_blocks` is the **per-source per-date target**, not a total budget. The same value applies independently to every source slot on every date. The validator's hard cap is 15 per source per date.

5. **Write `docs/dashboard/dashboard-data.json`.** Apply the curation rules below. Preserve every discovered date and every source slot per date. Always include `twitter`, `hackernews`, and `producthunt` keys, even when a source is missing.

6. **Validate the JSON.** Validation must pass before rendering. The validator cross-checks paths and locators against the inventory.

   ```bash
   python .claude/skills/daily-report-manager/scripts/validate_dashboard_data.py \
     docs/dashboard/dashboard-data.json \
     --inventory /tmp/drm-report-inventory.json
   ```

7. **Render the dashboard.**

   ```bash
   drm dashboard build \
     --input docs/dashboard/dashboard-data.json \
     --output docs/dashboard/index.html
   ```

If `drm` reports a non-zero exit code, treat the dashboard as not built. Fix the JSON (or the inventory if it's stale) and try again.

## Curation Rules

These rules exist because the dashboard is a high-signal reading surface, not a mirror of the source reports. The point is to make decisions easier for the reader.

### Per date

- Include every date discovered by the inventory.
- When at least two sources are available, write a short cross-source `summary` that names the day's main thread (model choice, infra incident, hot product, etc.). Keep it under 360 visible characters.
- When only one source is available, the date `summary` may be empty.

### Per report slot

- Always include all three source slots: `twitter`, `hackernews`, `producthunt`.
- Use `{"status": "missing"}` when there is no report file for that source/date — never omit the slot or invent content.
- For an available report, write a card with:
  - `summary`: ≤ 280 visible characters, restate the report's judgment in one or two sentences.
  - `highlights`: 2–5 short strings, ≤ 120 visible characters each. Prefer concrete entities over generic claims.
  - `metrics`: 0–4 key/value pairs from the report's data overview table when the values are stable and meaningful.

### Per selected block

- `max_blocks` applies **per source per date, independently**. A date with all three sources available should aim for up to `max_blocks × 3` total blocks across the date, not `max_blocks` total. Do not divide `max_blocks` across sources.
- For each available source on each date, select 1 to `max_blocks` blocks when the source has signal. Hard cap is 15 (validator enforced, per source). Default `max_blocks` is 15. When a source has sufficient signal, aim close to `max_blocks` rather than defaulting to 3–5 blocks.
- Worked example with `max_blocks = 15`: a date where `twitter` has 12 signal-bearing accounts, `hackernews` has 9 high-signal stories, and `producthunt` has 7 launches worth covering should produce roughly 12 + 9 + 7 = 28 blocks for the date. Truncate per source only when that source's signal runs out, never to keep the date's total down.
- Prefer blocks with decision value, cross-source relevance, unusually high signal, or future-reference value.
- Avoid empty-update blocks like `该账号今日无更新`, template scaffolding, or pure structural sections with no reader value.
- Use stable IDs in the form `{source}-{date}-{slug}` so links remain valid across rebuilds.
- `excerpt_markdown` is an excerpt or AI-written dashboard summary, not the full report section. Keep it ≤ 800 visible characters.
- Every block must include `source_report_path` and `source_locator.line_start` copied from the inventory. Do not guess.
- If an `available` or `incomplete` report has zero selected blocks, set `x_reason_no_blocks` (≤ 180 chars) explaining the low-signal condition.

### Search index

- Build one entry per selected block.
- `query_text` is a keyword surface, not prose — include entities, product names, project names, accounts, and durable concepts in both Chinese and English when both are useful. Keep ≤ 240 visible characters.
- `target_block_id` must reference a real selected block. The validator rejects dangling targets.
- `source_report_path` and `source_locator` should match the target block.

## Common Failure Modes

- **Stale inventory.** If you edit `docs/reports/*.md` between inventory and validation, line numbers will drift. Re-run the inventory after any edit.
- **Empty selected_blocks without reason.** The validator rejects this. Either add real blocks or set `x_reason_no_blocks`.
- **Mismatched paths.** `source_locator.path` must equal `source_report_path`. The validator catches this.
- **Duplicate block IDs.** Block IDs must be unique across the whole file, not just per report.
- **Search target not found.** `target_block_id` must point to a block that exists in `dates[].reports[].selected_blocks`.

## Report Back

After a successful build, tell the user:

- the JSON path: `docs/dashboard/dashboard-data.json`
- the HTML path: `docs/dashboard/index.html`
- date count, available report count, and selected block count from the `drm` output
- any source slots intentionally left as `missing`
- any `x_reason_no_blocks` entries you wrote

If `drm` failed, report the error and do not claim the dashboard was generated.
