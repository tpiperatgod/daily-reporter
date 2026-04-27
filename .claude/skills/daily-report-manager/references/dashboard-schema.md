# Dashboard Data Schema

This document is the operating contract for `docs/dashboard/dashboard-data.json`. The validator rejects anything that drifts from these rules.

## Top-level

```json
{
  "schema_version": 1,
  "generated_at": "2026-04-25T09:00:00Z",
  "source_reports_dir": "docs/reports",
  "dates": [...],
  "search_index": [...]
}
```

| Field | Required | Notes |
|---|---|---|
| `schema_version` | yes | Must equal integer `1`. |
| `generated_at` | yes | ISO-like timestamp string. |
| `source_reports_dir` | yes | Non-empty relative path. |
| `dates` | yes | Non-empty array, sorted newest first. |
| `search_index` | yes | Array. May be empty when there are no selected blocks. |

Unknown top-level keys are rejected unless prefixed with `x_`.

## `dates[]`

```json
{
  "date": "2026-04-25",
  "summary": "Cross-source daily thesis. May be empty when only one report exists.",
  "reports": {
    "twitter": {...},
    "hackernews": {...},
    "producthunt": {...}
  }
}
```

| Field | Required | Limit / Rule |
|---|---|---|
| `date` | yes | `YYYY-MM-DD`. |
| `summary` | yes | ≤ 360 visible chars. May be empty. |
| `reports` | yes | Must contain exactly the keys `twitter`, `hackernews`, `producthunt`. |

## `dates[].reports[source]`

The shape depends on `status`.

### `status: "missing"`

```json
{"status": "missing"}
```

No `card`, `selected_blocks`, or `source_report_path` allowed.

### `status: "available"` or `status: "incomplete"`

```json
{
  "status": "available",
  "source": "hackernews",
  "date": "2026-04-25",
  "title": "HN 高价值内容报告 — 2026-04-25",
  "source_report_path": "docs/reports/hn-daily-2026-04-25.md",
  "source_locator": {
    "path": "docs/reports/hn-daily-2026-04-25.md",
    "heading": "今日判断",
    "line_start": 9,
    "anchor": "今日判断"
  },
  "card": {
    "summary": "AI-curated short summary.",
    "highlights": ["...", "..."],
    "metrics": {"精选": "5", "拒选": "6"}
  },
  "selected_blocks": [...]
}
```

| Field | Limit / Rule |
|---|---|
| `source` | Must equal slot key. |
| `date` | Must equal parent date. |
| `title` | ≤ 120 visible chars, non-empty. |
| `source_report_path` | Must equal `source_locator.path`; must appear in inventory. |
| `source_locator.line_start` | Positive integer. |
| `card.summary` | ≤ 280 visible chars. May be empty. |
| `card.highlights` | 0–5 strings, each ≤ 120 chars. |
| `card.metrics` | 0–4 entries; keys/values each ≤ 40 chars. |
| `selected_blocks` | 0–8 entries. |

If `selected_blocks` is empty, add `x_reason_no_blocks` (≤ 180 chars) explaining why.

## `selected_blocks[]`

```json
{
  "id": "hn-2026-04-25-deepseek-v4",
  "title": "DeepSeek V4: benchmark 不等于体验",
  "kind": "pick",
  "reason": "Why this belongs in the dashboard.",
  "excerpt_markdown": "Short excerpt or AI-written summary.",
  "source_report_path": "docs/reports/hn-daily-2026-04-25.md",
  "source_locator": {
    "path": "docs/reports/hn-daily-2026-04-25.md",
    "heading": "1. DeepSeek V4 ...",
    "line_start": 29,
    "anchor": "1-deepseek-v4"
  }
}
```

| Field | Limit / Rule |
|---|---|
| `id` | Globally unique. Format: `{source}-{date}-{slug}`. |
| `title` | ≤ 120 visible chars, non-empty. |
| `kind` | One of `headline`, `pick`, `incident`, `tool`, `product`, `account`, `trend`, `metric`, `note`. |
| `reason` | ≤ 280 visible chars. |
| `excerpt_markdown` | ≤ 800 visible chars. Rendered through the safe Markdown renderer. |
| `source_report_path` | Must equal parent report's `source_report_path`. |
| `source_locator.line_start` | Positive integer; must match a heading in the inventory when `heading` is set. |

## `search_index[]`

```json
{
  "query_text": "DeepSeek V4 benchmark 体验 模型选型",
  "title": "DeepSeek V4: benchmark 不等于体验",
  "date": "2026-04-25",
  "source": "hackernews",
  "target_block_id": "hn-2026-04-25-deepseek-v4",
  "source_report_path": "docs/reports/hn-daily-2026-04-25.md",
  "source_locator": {
    "path": "docs/reports/hn-daily-2026-04-25.md",
    "line_start": 29,
    "anchor": "1-deepseek-v4"
  }
}
```

| Field | Limit / Rule |
|---|---|
| `query_text` | ≤ 240 visible chars, non-empty. |
| `title` | ≤ 120 visible chars. |
| `date` | `YYYY-MM-DD`. |
| `source` | One of `twitter`, `hackernews`, `producthunt`. |
| `target_block_id` | Must reference an existing selected block. |
| `source_report_path` | Must equal target block's `source_report_path`. |
| `source_locator.path` | Must equal `source_report_path`. |
| `source_locator.line_start` | Positive integer. |

## Allowed Statuses

- `available` — report file exists and has all expected sections.
- `incomplete` — report file exists but is missing expected sections; surface anyway.
- `missing` — report file does not exist for this date/source.

## Allowed Block Kinds

`headline`, `pick`, `incident`, `tool`, `product`, `account`, `trend`, `metric`, `note`.

## Compact Valid Example

```json
{
  "schema_version": 1,
  "generated_at": "2026-04-25T09:00:00Z",
  "source_reports_dir": "docs/reports",
  "dates": [
    {
      "date": "2026-04-25",
      "summary": "Today centers on model choice and toolchain trust.",
      "reports": {
        "twitter": {"status": "missing"},
        "hackernews": {
          "status": "available",
          "source": "hackernews",
          "date": "2026-04-25",
          "title": "HN 高价值内容报告 — 2026-04-25",
          "source_report_path": "docs/reports/hn-daily-2026-04-25.md",
          "source_locator": {
            "path": "docs/reports/hn-daily-2026-04-25.md",
            "heading": "今日判断",
            "line_start": 9,
            "anchor": "今日判断"
          },
          "card": {
            "summary": "DeepSeek and Claude Code discussions expose model-evaluation and trust risks.",
            "highlights": ["DeepSeek benchmarks do not settle coding experience."],
            "metrics": {"精选": "1"}
          },
          "selected_blocks": [
            {
              "id": "hn-2026-04-25-deepseek-v4",
              "title": "DeepSeek V4: benchmark 不等于体验",
              "kind": "pick",
              "reason": "Useful for model selection decisions.",
              "excerpt_markdown": "A short **curated** excerpt.",
              "source_report_path": "docs/reports/hn-daily-2026-04-25.md",
              "source_locator": {
                "path": "docs/reports/hn-daily-2026-04-25.md",
                "heading": "1. DeepSeek V4",
                "line_start": 29,
                "anchor": "1-deepseek-v4"
              }
            }
          ]
        },
        "producthunt": {"status": "missing"}
      }
    }
  ],
  "search_index": [
    {
      "query_text": "DeepSeek V4 benchmark coding experience 模型选型",
      "title": "DeepSeek V4: benchmark 不等于体验",
      "date": "2026-04-25",
      "source": "hackernews",
      "target_block_id": "hn-2026-04-25-deepseek-v4",
      "source_report_path": "docs/reports/hn-daily-2026-04-25.md",
      "source_locator": {
        "path": "docs/reports/hn-daily-2026-04-25.md",
        "line_start": 29,
        "anchor": "1-deepseek-v4"
      }
    }
  ]
}
```
