# Watchlists

Personal, user-curated account catalogs consumed by the `twitter-daily-report` skill.

Files in this directory are **gitignored** — each user maintains their own watchlist. The skill's default 29-account list is hard-coded into `../scripts/fetch_tweets.sh` (`ACCOUNTS` array) and `../scripts/analyze.py` (`ROLES`, `DISPLAY_NAMES`) so the pipeline works out of the box without any watchlist file.

## Layout

A watchlist is a markdown file grouping accounts by role. Minimum shape:

```markdown
## tech_educator
| Account | Name | Bio / 备注 |
|---------|------|-----------|
| @karpathy | Andrej Karpathy | ... |
```

Roles used by the skill: `tech_educator`, `ai_researcher`, `thought_leader`, `builder`, `tech_newscaster`, `practitioner`.

## Adding your own

1. Drop `my-watchlist.md` into this directory. It stays private.
2. To make it the active list, mirror the account handles into:
   - `../scripts/fetch_tweets.sh` — `ACCOUNTS` array
   - `../scripts/analyze.py` — `ROLES` and `DISPLAY_NAMES` tables

Drift between the markdown catalog and the two scripts is the most common source of report bugs — keep them in sync.
