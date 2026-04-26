"""Markdown parsing and safe rendering for drm."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from drm.anchors import make_unique_anchor, normalize_heading

REQUIRED_SECTIONS = {
    "twitter": ("今日头条", "今日数据概览"),
    "hackernews": ("今日判断", "精选条目", "数据概览"),
    "producthunt": ("今日判断", "深度精选", "数据概览"),
}

SUMMARY_SECTION = {
    "twitter": "今日头条",
    "hackernews": "今日判断",
    "producthunt": "今日判断",
}

HIGHLIGHTS_SECTION = {
    "twitter": "今日头条",
    "hackernews": "精选条目",
    "producthunt": "深度精选",
}

METRICS_SECTION = {
    "twitter": "今日数据概览",
    "hackernews": "数据概览",
    "producthunt": "数据概览",
}

STRIP_HIGHLIGHT_NUMBER = {
    "twitter": False,
    "hackernews": True,
    "producthunt": True,
}

TITLE_LIMIT = 80
SUMMARY_LIMIT = 280
HIGHLIGHT_LIMIT = 96
HIGHLIGHTS_MAX = 3
METRICS_MAX = 4

HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<heading>.+?)\s*$")


@dataclass(frozen=True)
class ReportSection:
    heading: str
    level: int
    anchor: str
    markdown: str
    text: str
    html: str


@dataclass(frozen=True)
class SearchBlock:
    heading: str
    level: int
    anchor: str
    parent_heading: str | None
    text: str


@dataclass(frozen=True)
class SourceCard:
    title: str
    summary: str
    highlights: list[str]
    metrics: dict[str, str]
    section_count: int
    block_count: int
    status: str


@dataclass(frozen=True)
class ParsedReport:
    title: str
    source: str
    date: str
    sections: list[ReportSection]
    search_blocks: list[SearchBlock]
    card: SourceCard
    status: str
    warnings: list[str] = field(default_factory=list)


def plain_text(markdown: str) -> str:
    """Return a plain-text approximation of markdown content."""
    lines: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", cell or "") for cell in cells):
                continue
            lines.append(" ".join(cell for cell in cells if cell))
            continue
        if stripped.startswith(">"):
            stripped = stripped.lstrip("> ").strip()
        if stripped.startswith(("- ", "* ")):
            stripped = stripped[2:].strip()
        elif re.match(r"^\d+\.\s+", stripped):
            stripped = re.sub(r"^\d+\.\s+", "", stripped)
        stripped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", stripped)
        stripped = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped)
        stripped = re.sub(r"`([^`]+)`", r"\1", stripped)
        lines.append(stripped)
    return "\n".join(lines)


_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_TABLE_DIVIDER_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def _is_safe_url(url: str) -> bool:
    return url.startswith(("http://", "https://", "#"))


def _render_inline(text: str) -> str:
    escaped = html.escape(text)

    code_holders: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_holders.append(f"<code>{match.group(1)}</code>")
        return f"\x00CODE{len(code_holders) - 1}\x00"

    escaped = _INLINE_CODE_RE.sub(stash_code, escaped)

    def link_sub(match: re.Match[str]) -> str:
        label = match.group(1)
        url = match.group(2)
        if not _is_safe_url(url):
            return match.group(0)
        return f'<a href="{url}" rel="noopener noreferrer">{label}</a>'

    escaped = _LINK_RE.sub(link_sub, escaped)
    escaped = _BOLD_RE.sub(r"<strong>\1</strong>", escaped)

    for index, replacement in enumerate(code_holders):
        escaped = escaped.replace(f"\x00CODE{index}\x00", replacement)

    return escaped


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _render_table(table_lines: list[str]) -> str:
    if len(table_lines) < 2:
        return ""
    header = _split_table_row(table_lines[0])
    body_lines = table_lines[2:]
    parts = ["<table>", "<thead>", "<tr>"]
    for cell in header:
        parts.append(f"<th>{_render_inline(cell)}</th>")
    parts.extend(["</tr>", "</thead>", "<tbody>"])
    for row in body_lines:
        cells = _split_table_row(row)
        parts.append("<tr>")
        for cell in cells:
            parts.append(f"<td>{_render_inline(cell)}</td>")
        parts.append("</tr>")
    parts.extend(["</tbody>", "</table>"])
    return "".join(parts)


def render_markdown(markdown: str, *, anchor_by_heading: dict[str, str] | None = None) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    i = 0
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        rendered = " ".join(_render_inline(line) for line in paragraph)
        out.append(f"<p>{rendered}</p>")
        paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group("marks"))
            heading_text = heading_match.group("heading").strip()
            normalized = normalize_heading(heading_text)
            anchor = (anchor_by_heading or {}).get(normalized)
            inner = _render_inline(heading_text)
            tag = f"h{min(level, 6)}"
            if anchor:
                out.append(f'<{tag} id="{anchor}">{inner}</{tag}>')
            else:
                out.append(f"<{tag}>{inner}</{tag}>")
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and _TABLE_DIVIDER_RE.match(lines[i + 1]):
            flush_paragraph()
            table_lines = [line, lines[i + 1]]
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                table_lines.append(lines[j])
                j += 1
            out.append(_render_table(table_lines))
            i = j
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").lstrip())
                i += 1
            inner = " ".join(_render_inline(line) for line in quote_lines if line)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            items: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(("- ", "* ")):
                items.append(lines[i].strip()[2:])
                i += 1
            out.append("<ul>")
            for item in items:
                out.append(f"<li>{_render_inline(item)}</li>")
            out.append("</ul>")
            continue

        ol_match = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if ol_match:
            flush_paragraph()
            items = []
            while i < len(lines):
                m = re.match(r"^\s*\d+\.\s+(.*)$", lines[i])
                if not m:
                    break
                items.append(m.group(1))
                i += 1
            out.append("<ol>")
            for item in items:
                out.append(f"<li>{_render_inline(item)}</li>")
            out.append("</ol>")
            continue

        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    return "\n".join(out)


def truncate_visible(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def extract_first_paragraph(section_markdown: str) -> str:
    paragraph: list[str] = []
    for line in section_markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if HEADING_RE.match(line) or stripped.startswith(("|", ">", "- ", "* ")):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    text = " ".join(paragraph)
    text = _LINK_RE.sub(r"\1", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    return text


def extract_child_headings(search_blocks: list[SearchBlock], parent_heading: str, *, strip_number: bool) -> list[str]:
    items: list[str] = []
    for block in search_blocks:
        if block.level != 3 or block.parent_heading != parent_heading:
            continue
        heading = block.heading
        if strip_number:
            heading = re.sub(r"^\d+\.\s*", "", heading)
        items.append(heading)
    return items


def extract_table_metrics(section_markdown: str, *, limit: int = METRICS_MAX) -> dict[str, str]:
    lines = [line for line in section_markdown.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return {}
    if not _TABLE_DIVIDER_RE.match(lines[1]):
        return {}
    metrics: dict[str, str] = {}
    for row in lines[2:]:
        cells = _split_table_row(row)
        if len(cells) < 2:
            continue
        key = cells[0]
        value = cells[1]
        if not key:
            continue
        metrics[key] = value
        if len(metrics) >= limit:
            break
    return metrics


def build_source_card(
    *,
    title: str,
    source: str,
    sections: list[ReportSection],
    search_blocks: list[SearchBlock],
    status: str,
    warnings: list[str],
) -> SourceCard:
    by_heading = {section.heading: section for section in sections}

    summary_heading = SUMMARY_SECTION.get(source)
    summary = ""
    if summary_heading and summary_heading in by_heading:
        summary = extract_first_paragraph(by_heading[summary_heading].markdown)
    summary = truncate_visible(summary, SUMMARY_LIMIT)

    highlights_heading = HIGHLIGHTS_SECTION.get(source)
    highlights: list[str] = []
    if highlights_heading:
        raw_highlights = extract_child_headings(
            search_blocks,
            highlights_heading,
            strip_number=STRIP_HIGHLIGHT_NUMBER.get(source, False),
        )
        highlights = [truncate_visible(item, HIGHLIGHT_LIMIT) for item in raw_highlights[:HIGHLIGHTS_MAX]]

    metrics: dict[str, str] = {}
    metrics_heading = METRICS_SECTION.get(source)
    if metrics_heading and metrics_heading in by_heading:
        metrics = extract_table_metrics(by_heading[metrics_heading].markdown)

    return SourceCard(
        title=truncate_visible(title, TITLE_LIMIT),
        summary=summary,
        highlights=highlights,
        metrics=metrics,
        section_count=len(sections),
        block_count=len(search_blocks),
        status=status,
    )


def _slice(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start:end])


def parse_report_markdown(markdown: str, *, source: str, date: str) -> ParsedReport:
    lines = markdown.splitlines()

    title = ""
    headings: list[tuple[int, str, str, int]] = []
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group("marks"))
        raw = m.group("heading")
        if level == 1 and not title:
            title = raw.strip()
            continue
        if level in (2, 3):
            headings.append((level, raw, normalize_heading(raw), i))

    used_anchors: set[str] = set()

    sections: list[ReportSection] = []
    search_blocks: list[SearchBlock] = []

    for idx, (level, _raw, normalized, line_idx) in enumerate(headings):
        end_line = len(lines)
        for j in range(idx + 1, len(headings)):
            if headings[j][0] <= level:
                end_line = headings[j][3]
                break

        block_md = _slice(lines, line_idx + 1, end_line)
        anchor = make_unique_anchor(normalized, used_anchors)

        if level == 2:
            sections.append(
                ReportSection(
                    heading=normalized,
                    level=2,
                    anchor=anchor,
                    markdown=block_md,
                    text=plain_text(block_md),
                    html=render_markdown(block_md),
                )
            )

        parent: str | None = None
        if level == 3:
            for j in range(idx - 1, -1, -1):
                if headings[j][0] == 2:
                    parent = headings[j][2]
                    break

        search_blocks.append(
            SearchBlock(
                heading=normalized,
                level=level,
                anchor=anchor,
                parent_heading=parent,
                text=plain_text(block_md),
            )
        )

    required = REQUIRED_SECTIONS.get(source, ())
    section_headings = {section.heading for section in sections}
    warnings: list[str] = []
    for req in required:
        if req not in section_headings:
            warnings.append(f"missing required section: {req}")
    status = "incomplete" if warnings else "available"

    card = build_source_card(
        title=title,
        source=source,
        sections=sections,
        search_blocks=search_blocks,
        status=status,
        warnings=warnings,
    )

    return ParsedReport(
        title=title,
        source=source,
        date=date,
        sections=sections,
        search_blocks=search_blocks,
        card=card,
        status=status,
        warnings=warnings,
    )
