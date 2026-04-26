"""Dashboard model building for drm."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from drm.parser import ParsedReport, ReportSection, SearchBlock, SourceCard, parse_report_markdown
from drm.reports import SOURCE_ORDER, ReportRef


@dataclass(frozen=True)
class DashboardModel:
    dates: list[str]
    reports_by_date: dict[str, dict[str, dict]]
    search_index: list[dict]
    generated_at: str
    date_summaries: dict[str, str] | None = None


def serialize_section(section: ReportSection) -> dict:
    return {
        "heading": section.heading,
        "level": section.level,
        "anchor": section.anchor,
        "html": section.html,
    }


def serialize_card(card: SourceCard) -> dict:
    return {
        "title": card.title,
        "summary": card.summary,
        "highlights": list(card.highlights),
        "metrics": dict(card.metrics),
        "section_count": card.section_count,
        "block_count": card.block_count,
        "status": card.status,
    }


def serialize_report(report: ParsedReport) -> dict:
    return {
        "status": report.status,
        "source": report.source,
        "date": report.date,
        "title": report.title,
        "warnings": list(report.warnings),
        "sections": [serialize_section(section) for section in report.sections],
        "card": serialize_card(report.card),
    }


def _serialize_search_block(report: ParsedReport, block: SearchBlock) -> dict:
    return {
        "heading": block.heading,
        "level": block.level,
        "anchor": block.anchor,
        "parent_heading": block.parent_heading,
        "text": block.text,
        "source": report.source,
        "date": report.date,
    }


def build_dashboard_model(report_refs: list[ReportRef]) -> DashboardModel:
    parsed_by_key: dict[tuple[str, str], ParsedReport] = {}
    dates_set: set[str] = set()

    for ref in report_refs:
        markdown = ref.path.read_text(encoding="utf-8")
        parsed = parse_report_markdown(markdown, source=ref.source, date=ref.date)
        parsed_by_key[(ref.date, ref.source)] = parsed
        dates_set.add(ref.date)

    dates = sorted(dates_set, reverse=True)

    reports_by_date: dict[str, dict[str, dict]] = {}
    search_index: list[dict] = []
    for date in dates:
        slots: dict[str, dict] = {}
        for source in SOURCE_ORDER:
            parsed = parsed_by_key.get((date, source))
            if parsed is None:
                slots[source] = {"status": "missing", "source": source, "date": date}
                continue
            slots[source] = serialize_report(parsed)
            for block in parsed.search_blocks:
                search_index.append(_serialize_search_block(parsed, block))
        reports_by_date[date] = slots

    return DashboardModel(
        dates=dates,
        reports_by_date=reports_by_date,
        search_index=search_index,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
