"""Curated dashboard JSON loading and validation."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from drm.dashboard import DashboardModel
from drm.errors import InputError
from drm.parser import render_markdown
from drm.reports import SOURCE_ORDER

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+")
TWEET_METRIC_RE = re.compile(r"♥\s*\d+\s*🔁\s*\d+\s*💬\s*\d+")
ALLOWED_STATUSES = {"available", "missing", "incomplete"}
ALLOWED_KINDS = {"headline", "pick", "incident", "tool", "product", "account", "trend", "metric", "note"}
REQUIRED_SOURCES = ("twitter", "hackernews", "producthunt")

LIMIT_SUMMARY = 360
LIMIT_TITLE = 120
LIMIT_CARD_SUMMARY = 280
LIMIT_HIGHLIGHT = 120
LIMIT_METRIC_KEY = 40
LIMIT_METRIC_VALUE = 40
LIMIT_REASON = 280
LIMIT_EXCERPT = 800
LIMIT_QUERY_TEXT = 240
LIMIT_REASON_NO_BLOCKS = 180
MAX_HIGHLIGHTS = 5
MAX_METRICS = 4
MAX_BLOCKS = 15


def load_dashboard_data(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise InputError(f"dashboard data input does not exist: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid dashboard data JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise InputError("dashboard data root must be an object")
    return data


def _fail(message: str) -> None:
    raise InputError(f"invalid dashboard data: {message}")


def _visible_len(value: str) -> int:
    return len(value.strip())


def _require_str(obj: dict[str, Any], key: str, *, max_len: int | None = None, allow_empty: bool = False) -> str:
    value = obj.get(key)
    if not isinstance(value, str):
        _fail(f"{key} must be a string")
    if not allow_empty and not value.strip():
        _fail(f"{key} must not be empty")
    if max_len is not None and _visible_len(value) > max_len:
        _fail(f"{key} exceeds {max_len} characters")
    return value


def _require_int(obj: dict[str, Any], key: str, *, positive: bool = False) -> int:
    value = obj.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        _fail(f"{key} must be an integer")
    if positive and value <= 0:
        _fail(f"{key} must be a positive integer")
    return value


def _validate_locator(locator: Any, *, path: str, context: str) -> None:
    if not isinstance(locator, dict):
        _fail(f"{context}.source_locator must be an object")
    loc_path = _require_str(locator, "path")
    if loc_path != path:
        _fail(f"{context}.source_locator.path must match source_report_path")
    line_start = locator.get("line_start")
    if not isinstance(line_start, int) or isinstance(line_start, bool) or line_start <= 0:
        _fail(f"{context}.source_locator.line_start must be a positive integer")
    if "line_end" in locator:
        line_end = locator["line_end"]
        if not isinstance(line_end, int) or isinstance(line_end, bool) or line_end < line_start:
            _fail(f"{context}.source_locator.line_end must be an integer >= line_start")


def _check_top_level_unknowns(data: dict[str, Any]) -> None:
    known = {"schema_version", "generated_at", "source_reports_dir", "dates", "search_index"}
    for key in data:
        if key in known:
            continue
        if not key.startswith("x_"):
            _fail(f"unknown top-level field: {key}")


def _inventory_paths(inventory: dict[str, Any] | None) -> set[str] | None:
    if inventory is None:
        return None
    reports = inventory.get("reports")
    if not isinstance(reports, list):
        _fail("inventory.reports must be an array")
    return {report["path"] for report in reports if isinstance(report, dict) and isinstance(report.get("path"), str)}


def _inventory_locators(inventory: dict[str, Any] | None) -> set[tuple[str, int]] | None:
    if inventory is None:
        return None
    locators: set[tuple[str, int]] = set()
    for report in inventory.get("reports", []):
        if not isinstance(report, dict):
            continue
        path = report.get("path")
        for heading in report.get("headings", []) or []:
            if not isinstance(heading, dict):
                continue
            line_start = heading.get("line_start")
            if isinstance(path, str) and isinstance(line_start, int) and not isinstance(line_start, bool):
                locators.add((path, line_start))
    return locators


def _validate_card(card: Any) -> None:
    if not isinstance(card, dict):
        _fail("card must be an object")
    _require_str(card, "summary", max_len=LIMIT_CARD_SUMMARY, allow_empty=True)
    highlights = card.get("highlights")
    if not isinstance(highlights, list):
        _fail("card.highlights must be an array")
    if len(highlights) > MAX_HIGHLIGHTS:
        _fail(f"card.highlights exceeds {MAX_HIGHLIGHTS} items")
    for item in highlights:
        if not isinstance(item, str):
            _fail("card.highlights items must be strings")
        if _visible_len(item) > LIMIT_HIGHLIGHT:
            _fail(f"card.highlight exceeds {LIMIT_HIGHLIGHT} characters")
    metrics = card.get("metrics")
    if not isinstance(metrics, dict):
        _fail("card.metrics must be an object")
    if len(metrics) > MAX_METRICS:
        _fail(f"card.metrics exceeds {MAX_METRICS} keys")
    for key, value in metrics.items():
        if not isinstance(key, str) or _visible_len(key) > LIMIT_METRIC_KEY:
            _fail(f"card.metrics keys must be strings <= {LIMIT_METRIC_KEY} chars")
        if not isinstance(value, str) or _visible_len(value) > LIMIT_METRIC_VALUE:
            _fail(f"card.metrics values must be strings <= {LIMIT_METRIC_VALUE} chars")


def _validate_selected_block(
    block: Any,
    *,
    parent_path: str,
    seen_ids: set[str],
    inventory_paths: set[str] | None,
    inventory_locators: set[tuple[str, int]] | None,
) -> str:
    if not isinstance(block, dict):
        _fail("selected_blocks items must be objects")
    block_id = _require_str(block, "id")
    if block_id in seen_ids:
        _fail(f"duplicate selected block id: {block_id}")
    seen_ids.add(block_id)
    _require_str(block, "title", max_len=LIMIT_TITLE)
    kind = _require_str(block, "kind")
    if kind not in ALLOWED_KINDS:
        _fail(f"selected_block.kind not allowed: {kind}")
    _require_str(block, "reason", max_len=LIMIT_REASON)
    _require_str(block, "excerpt_markdown", max_len=LIMIT_EXCERPT)
    block_path = _require_str(block, "source_report_path")
    if block_path != parent_path:
        _fail("selected_block.source_report_path must match parent report")
    locator = block.get("source_locator")
    _validate_locator(locator, path=block_path, context=f"selected_block[{block_id}]")
    if inventory_paths is not None and block_path not in inventory_paths:
        _fail(f"selected_block.source_report_path not in inventory: {block_path}")
    if inventory_locators is not None and locator.get("heading"):
        if (locator["path"], locator["line_start"]) not in inventory_locators:
            _fail(
                f"selected_block.source_locator does not match inventory heading: "
                f"{locator['path']}:{locator['line_start']}"
            )
    return block_id


def _validate_report(
    slot: Any,
    *,
    source: str,
    date: str,
    seen_ids: set[str],
    inventory_paths: set[str] | None,
    inventory_locators: set[tuple[str, int]] | None,
) -> None:
    if not isinstance(slot, dict):
        _fail(f"reports.{source} must be an object")
    status = slot.get("status")
    if status not in ALLOWED_STATUSES:
        _fail(f"reports.{source}.status not allowed: {status}")

    if status == "missing":
        for forbidden in ("card", "selected_blocks", "source_report_path"):
            if forbidden in slot:
                _fail(f"missing report must not include {forbidden}")
        return

    if slot.get("source") != source:
        _fail(f"reports.{source}.source must match slot key")
    if slot.get("date") != date:
        _fail(f"reports.{source}.date must match parent date")
    _require_str(slot, "title", max_len=LIMIT_TITLE)
    report_path = _require_str(slot, "source_report_path")
    locator = slot.get("source_locator")
    _validate_locator(locator, path=report_path, context=f"reports.{source}")
    if inventory_paths is not None and report_path not in inventory_paths:
        _fail(f"reports.{source}.source_report_path not in inventory: {report_path}")
    if inventory_locators is not None and locator.get("heading"):
        if (locator["path"], locator["line_start"]) not in inventory_locators:
            _fail(
                f"reports.{source}.source_locator does not match inventory heading: "
                f"{locator['path']}:{locator['line_start']}"
            )

    _validate_card(slot.get("card"))

    blocks = slot.get("selected_blocks")
    if not isinstance(blocks, list):
        _fail(f"reports.{source}.selected_blocks must be an array")
    if len(blocks) > MAX_BLOCKS:
        _fail(f"reports.{source}.selected_blocks exceeds {MAX_BLOCKS} items")
    if len(blocks) == 0:
        reason = slot.get("x_reason_no_blocks")
        if not isinstance(reason, str) or not reason.strip():
            _fail(f"reports.{source} with zero selected_blocks must include x_reason_no_blocks")
        if _visible_len(reason) > LIMIT_REASON_NO_BLOCKS:
            _fail(f"reports.{source}.x_reason_no_blocks exceeds {LIMIT_REASON_NO_BLOCKS} characters")
    for block in blocks:
        _validate_selected_block(
            block,
            parent_path=report_path,
            seen_ids=seen_ids,
            inventory_paths=inventory_paths,
            inventory_locators=inventory_locators,
        )


def _validate_search_entry(entry: Any, *, all_block_ids: set[str], all_blocks_by_id: dict[str, dict]) -> None:
    if not isinstance(entry, dict):
        _fail("search_index items must be objects")
    _require_str(entry, "query_text", max_len=LIMIT_QUERY_TEXT)
    _require_str(entry, "title", max_len=LIMIT_TITLE)
    date = _require_str(entry, "date")
    if not DATE_RE.match(date):
        _fail(f"search_index.date must be YYYY-MM-DD: {date}")
    source = _require_str(entry, "source")
    if source not in REQUIRED_SOURCES:
        _fail(f"search_index.source not allowed: {source}")
    target = _require_str(entry, "target_block_id")
    if target not in all_block_ids:
        _fail(f"search_index.target_block_id refers to missing block: {target}")
    target_block = all_blocks_by_id[target]
    report_path = _require_str(entry, "source_report_path")
    if report_path != target_block["source_report_path"]:
        _fail("search_index.source_report_path must match target block")
    locator = entry.get("source_locator")
    if not isinstance(locator, dict):
        _fail("search_index.source_locator must be an object")
    if locator.get("path") != report_path:
        _fail("search_index.source_locator.path must match source_report_path")
    line_start = locator.get("line_start")
    if not isinstance(line_start, int) or isinstance(line_start, bool) or line_start <= 0:
            _fail("search_index.source_locator.line_start must be a positive integer")


def _extract_markdown_links(markdown: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in MARKDOWN_LINK_RE.finditer(markdown):
        label = re.sub(r"\s+", " ", match.group(1)).strip() or "Original"
        url = match.group(2).strip()
        if url in seen:
            continue
        seen.add(url)
        links.append({"label": label, "url": url})
    return links


def _section_markdown_for_locator(path: str, locator: dict[str, Any]) -> str:
    line_start = locator.get("line_start")
    if not isinstance(line_start, int) or isinstance(line_start, bool) or line_start <= 0:
        return ""
    report_path = Path(path)
    if not report_path.exists() or not report_path.is_file():
        return ""
    try:
        lines = report_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    start = min(max(line_start - 1, 0), len(lines))
    if start >= len(lines):
        return ""

    heading_match = HEADING_RE.match(lines[start])
    heading_level = len(heading_match.group(1)) if heading_match else None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        next_heading = HEADING_RE.match(lines[index])
        if next_heading and (heading_level is None or len(next_heading.group(1)) <= heading_level):
            end = index
            break
    return "\n".join(lines[start:end])


def _tweet_metric_marker(markdown: str) -> str | None:
    match = TWEET_METRIC_RE.search(markdown)
    if match is None:
        return None
    return re.sub(r"\s+", " ", match.group(0)).strip()


def _links_for_matching_tweet_metrics(section_markdown: str, excerpt_markdown: str) -> list[dict[str, str]]:
    marker = _tweet_metric_marker(excerpt_markdown)
    if marker is None:
        return []
    for line in section_markdown.splitlines():
        normalized = re.sub(r"\s+", " ", line).strip()
        if marker not in normalized:
            continue
        links = _extract_markdown_links(line)
        if links:
            return links
    return []


def _preferred_original_links(links: list[dict[str, str]]) -> list[dict[str, str]]:
    preferred_labels = ("原文", "HN 讨论", "Product Hunt", "Website")
    preferred = [
        link
        for link in links
        if any(link["label"].lower() == label.lower() for label in preferred_labels)
        or link["label"].startswith("item?id=")
    ]
    return preferred or links


def _original_links_for_block(block: dict[str, Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_many(items: list[dict[str, str]]) -> None:
        for item in items:
            url = item["url"]
            if url in seen:
                continue
            seen.add(url)
            links.append(item)

    excerpt_markdown = block.get("excerpt_markdown", "")
    add_many(_extract_markdown_links(excerpt_markdown))
    if links:
        return links
    locator = block.get("source_locator")
    if isinstance(locator, dict):
        section_markdown = _section_markdown_for_locator(block.get("source_report_path", ""), locator)
        metric_links = _links_for_matching_tweet_metrics(section_markdown, excerpt_markdown)
        add_many(metric_links or _preferred_original_links(_extract_markdown_links(section_markdown)))
    return links


def validate_dashboard_data(data: dict[str, Any], *, inventory: dict[str, Any] | None = None) -> None:
    if not isinstance(data, dict):
        _fail("root must be an object")
    _check_top_level_unknowns(data)

    if data.get("schema_version") != 1:
        _fail("schema_version must equal 1")
    _require_str(data, "generated_at")
    _require_str(data, "source_reports_dir")

    dates = data.get("dates")
    if not isinstance(dates, list) or not dates:
        _fail("dates must be a non-empty array")

    date_keys = [item.get("date") if isinstance(item, dict) else None for item in dates]
    sorted_desc = sorted([d for d in date_keys if isinstance(d, str)], reverse=True)
    if [d for d in date_keys if isinstance(d, str)] != sorted_desc:
        _fail("dates must be sorted newest first")

    inv_paths = _inventory_paths(inventory)
    inv_locators = _inventory_locators(inventory)

    all_block_ids: set[str] = set()
    all_blocks_by_id: dict[str, dict] = {}

    for date_record in dates:
        if not isinstance(date_record, dict):
            _fail("dates items must be objects")
        date = _require_str(date_record, "date")
        if not DATE_RE.match(date):
            _fail(f"date must be YYYY-MM-DD: {date}")
        _require_str(date_record, "summary", max_len=LIMIT_SUMMARY, allow_empty=True)
        reports = date_record.get("reports")
        if not isinstance(reports, dict):
            _fail(f"reports for date {date} must be an object")
        if set(reports.keys()) != set(REQUIRED_SOURCES):
            _fail(f"reports for date {date} must contain exactly: {sorted(REQUIRED_SOURCES)}")
        for source in REQUIRED_SOURCES:
            seen_ids_for_report: set[str] = set()
            _validate_report(
                reports[source],
                source=source,
                date=date,
                seen_ids=seen_ids_for_report,
                inventory_paths=inv_paths,
                inventory_locators=inv_locators,
            )
            for block in reports[source].get("selected_blocks", []) or []:
                if isinstance(block, dict) and isinstance(block.get("id"), str):
                    if block["id"] in all_block_ids:
                        _fail(f"duplicate selected block id across file: {block['id']}")
                    all_block_ids.add(block["id"])
                    all_blocks_by_id[block["id"]] = block

    search_index = data.get("search_index")
    if not isinstance(search_index, list):
        _fail("search_index must be an array")
    for entry in search_index:
        _validate_search_entry(entry, all_block_ids=all_block_ids, all_blocks_by_id=all_blocks_by_id)


def build_dashboard_model_from_data(data: dict[str, Any]) -> DashboardModel:
    validate_dashboard_data(data)
    reports_by_date: dict[str, dict[str, dict[str, Any]]] = {}
    for date_record in data["dates"]:
        slots: dict[str, dict[str, Any]] = {}
        for source in SOURCE_ORDER:
            slot = copy.deepcopy(date_record["reports"][source])
            if slot.get("status") in {"available", "incomplete"}:
                for block in slot.get("selected_blocks", []) or []:
                    block["html"] = render_markdown(block.get("excerpt_markdown", ""))
                    block["original_links"] = _original_links_for_block(block)
            slots[source] = slot
        reports_by_date[date_record["date"]] = slots
    return DashboardModel(
        dates=[item["date"] for item in data["dates"]],
        reports_by_date=reports_by_date,
        search_index=copy.deepcopy(data["search_index"]),
        generated_at=data["generated_at"],
        date_summaries={item["date"]: item.get("summary", "") for item in data["dates"]},
    )
