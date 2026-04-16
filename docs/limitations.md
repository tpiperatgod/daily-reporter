# Limitations

This page collects the main behavior gaps and caveats that users and harness agents should know about today.

## Checkpoint State

`--state-file path.json` enables checkpoint persistence.

Today the file stores metadata such as the highest observed `since_id`, for example:

```json
{
  "since_id": "1900000000000000000",
  "last_username": "karpathy"
}
```

Important: the checkpoint is currently written and loaded, but it is not yet applied to upstream request filtering.
If you need deterministic boundaries today, pass `--since`, `--until`, and `--limit` explicitly.

## Known Limitations

- `twx trending` currently searches for the literal query `"trending"` and does not use a dedicated trends endpoint.
- Pagination is not implemented; commands only return the first page.
- Search and trending rely on response-shape fallbacks because twitterapi.io can return tweets in different locations.
- `TWX_DEFAULT_LIMIT` is parsed by config, but command defaults are still hard-coded to `20`.

## What This Means For Agents

- Do not assume `--state-file` gives incremental upstream fetching yet.
- Do not assume `paging.has_more=true` means pagination is available now; current commands always return a single page.
- If you need exact rate-limit or endpoint behavior, validate against the upstream API because `trending` is currently implemented as a search wrapper.

## Related Docs

- [Quickstart](quickstart.md)
- [Commands](commands.md)
- [Contracts](contracts.md)
