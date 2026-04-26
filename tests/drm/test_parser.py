"""Tests for markdown report parsing."""

from __future__ import annotations

from drm.parser import parse_report_markdown


def test_parse_twitter_report_sections_and_blocks() -> None:
    markdown = """# Tech Twitter 日报 — 2026-04-24

## 📰 今日头条

### 1. DeepSeek-V4 开源发布

> 内容

## 📊 今日数据概览

| 指标 | 数值 |
|---|---:|
| 当日总推文 | 42 |
"""

    report = parse_report_markdown(markdown, source="twitter", date="2026-04-24")

    assert report.title == "Tech Twitter 日报 — 2026-04-24"
    assert report.status == "available"
    assert [section.heading for section in report.sections] == ["今日头条", "今日数据概览"]
    assert [block.heading for block in report.search_blocks] == [
        "今日头条",
        "1. DeepSeek-V4 开源发布",
        "今日数据概览",
    ]
    assert report.search_blocks[1].parent_heading == "今日头条"


def test_missing_required_section_marks_report_incomplete() -> None:
    markdown = """# HN 高价值内容报告 — 2026-04-25

## 今日判断

正文
"""

    report = parse_report_markdown(markdown, source="hackernews", date="2026-04-25")

    assert report.status == "incomplete"
    assert "missing required section: 精选条目" in report.warnings
    assert "missing required section: 数据概览" in report.warnings


def test_optional_section_missing_is_warning_only() -> None:
    markdown = """# Product Hunt Daily Scout - 2026-04-24

## 今日判断

正文

## 深度精选

### 1. Product - Tagline

正文

## 数据概览

| 指标 | 数值 |
|---|---:|
| Final picks | 1 |
"""

    report = parse_report_markdown(markdown, source="producthunt", date="2026-04-24")

    assert report.status == "available"


def test_renderer_escapes_raw_html_and_script() -> None:
    markdown = """# Report

## 今日判断

<script>alert("x")</script>

<div onclick="boom()">raw</div>
"""

    report = parse_report_markdown(markdown, source="hackernews", date="2026-04-25")

    html = report.sections[0].html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "onclick" in html
    assert "&lt;div" in html


def test_renderer_supports_tables_links_bold_and_blockquotes() -> None:
    markdown = """# Report

## 今日判断

> A **strong** claim with [link](https://example.com).

| 指标 | 数值 |
|---|---:|
| Final picks | 4 |
"""

    report = parse_report_markdown(markdown, source="producthunt", date="2026-04-24")

    html = report.sections[0].html
    assert "<blockquote>" in html
    assert "<strong>strong</strong>" in html
    assert '<a href="https://example.com"' in html
    assert "<table>" in html
    assert "<td>Final picks</td>" in html


def test_twitter_card_is_bounded() -> None:
    markdown = """# Tech Twitter 日报 — 2026-04-24

## 📰 今日头条

### 1. First headline

正文

### 2. Second headline

正文

### 3. Third headline

正文

### 4. Fourth headline

正文

## 📊 今日数据概览

| 指标 | 数值 |
|---|---:|
| 当日总推文 | 42 |
| 当日活跃账号 | 12 |
| 高频关键词 | AI, infra |
| 中/英文推文比 | 20 / 22 |
| extra | ignored |
"""

    report = parse_report_markdown(markdown, source="twitter", date="2026-04-24")

    assert report.card.status == "available"
    assert len(report.card.summary) <= 280
    assert report.card.highlights == ["1. First headline", "2. Second headline", "3. Third headline"]
    assert list(report.card.metrics) == ["当日总推文", "当日活跃账号", "高频关键词", "中/英文推文比"]


def test_hn_card_uses_judgment_and_quick_nav() -> None:
    markdown = """# HN 高价值内容报告 — 2026-04-25

## 今日判断

今天的主线是模型选型和工具链信任。

## 快速导航

| # | 主题 | 类型 | 为什么值得读 | HN |
|---:|---|---|---|---|
| 1 | DeepSeek V4 | tool | 模型选型 | [讨论](https://news.ycombinator.com/item?id=1) |

## 精选条目

### 1. DeepSeek V4

正文

## 数据概览

| 指标 | 数值 |
|---|---:|
| 最终入选 | 1 |
"""

    report = parse_report_markdown(markdown, source="hackernews", date="2026-04-25")

    assert report.card.summary == "今天的主线是模型选型和工具链信任。"
    assert report.card.highlights == ["DeepSeek V4"]
    assert report.card.metrics == {"最终入选": "1"}
