"""Static HTML template rendering for drm."""

from __future__ import annotations

import json

from drm.dashboard import DashboardModel


def safe_json_for_script(data: object) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("</script", "\\u003c/script")
    )


_CSS = """
* { box-sizing: border-box; }
:root {
  --bg: #f5f7f4;
  --paper: #ffffff;
  --paper-2: #eef4ef;
  --line: #dfe6de;
  --line-strong: #c9d5cc;
  --text: #2a2f2a;
  --muted: #647066;
  --soft: #89948b;
  --accent: #a44d2f;
  --accent-dark: #74351f;
  --green: #356a4f;
  --blue: #315f7d;
  --dark: #1f1b17;
  --shadow: 0 1px 2px rgba(45,42,38,.07), 0 10px 28px rgba(45,42,38,.08);
}
html, body {
  margin: 0;
  padding: 0;
  min-height: 100%;
  background: var(--bg);
  color: var(--text);
  font: 14px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
body { overflow-x: hidden; }
button, input, select { font: inherit; }
button:focus-visible,
input:focus-visible,
select:focus-visible,
a:focus-visible {
  outline: 3px solid rgba(164,77,47,.22);
  outline-offset: 2px;
}
.rw-page {
  min-height: 100vh;
  padding: 24px;
  background:
    linear-gradient(180deg, #f7f9f5 0%, #f3f6f1 58%, #edf3ef 100%);
}
.rw-shell {
  max-width: 1360px;
  margin: 0 auto;
}
.rw-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: start;
  padding: 18px 0 22px;
  border-bottom: 1px solid var(--line);
}
.rw-kicker {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 760;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.rw-title {
  margin: 0;
  color: var(--dark);
  font-size: clamp(30px, 4vw, 48px);
  line-height: 1.05;
  font-weight: 820;
  letter-spacing: 0;
}
.rw-subtitle {
  max-width: 760px;
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.75;
}
.rw-controls {
  display: grid;
  grid-template-columns: 160px minmax(240px, 340px) auto;
  gap: 10px;
  align-items: center;
}
.rw-select,
.rw-search,
.rw-button {
  min-height: 42px;
  border-radius: 8px;
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--text);
}
.rw-select {
  width: 100%;
  padding: 0 12px;
  cursor: pointer;
}
.rw-search-wrap {
  position: relative;
  min-width: 0;
}
.rw-search-mark {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--soft);
  font-weight: 800;
  pointer-events: none;
}
.rw-search {
  width: 100%;
  padding: 0 12px 0 34px;
  outline: none;
}
.rw-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 14px;
  font-weight: 760;
  cursor: pointer;
  white-space: nowrap;
}
.rw-button:hover {
  border-color: var(--accent);
  color: var(--accent-dark);
}
.rw-button-primary {
  border-color: var(--dark);
  background: var(--dark);
  color: #fff;
}
.rw-button-primary:hover {
  border-color: var(--accent-dark);
  background: var(--accent-dark);
  color: #fff;
}
.rw-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0;
}
.rw-kpi {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
  padding: 14px;
  box-shadow: 0 1px 1px rgba(45,42,38,.04);
}
.rw-kpi-label {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 720;
  text-transform: uppercase;
  letter-spacing: .06em;
}
.rw-kpi-value {
  margin: 6px 0 0;
  color: var(--dark);
  font-size: 28px;
  line-height: 1.1;
  font-weight: 820;
  font-variant-numeric: tabular-nums;
}
.rw-kpi-note {
  margin: 8px 0 0;
  color: var(--soft);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rw-workspace {
  display: grid;
  grid-template-columns: minmax(320px, .86fr) minmax(0, 1.34fr);
  gap: 18px;
  align-items: start;
}
.rw-panel,
.rw-detail-panel,
.rw-bottom-panel {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
  box-shadow: var(--shadow);
}
.rw-panel {
  min-width: 0;
  padding: 16px;
}
.rw-detail-panel {
  position: sticky;
  top: 16px;
  min-width: 0;
  padding: 18px;
}
.rw-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}
.rw-section-eyebrow {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
  text-transform: uppercase;
  letter-spacing: .06em;
}
.rw-section-title {
  margin: 4px 0 0;
  color: var(--dark);
  font-size: 18px;
  line-height: 1.25;
  font-weight: 820;
}
.rw-count {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 10px;
  color: var(--muted);
  background: var(--paper-2);
  font-size: 12px;
  font-weight: 760;
  white-space: nowrap;
}
.rw-brief {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #f5f8f2;
  padding: 14px;
  margin-bottom: 14px;
}
.rw-brief-title {
  margin: 0 0 8px;
  color: var(--dark);
  font-size: 13px;
  font-weight: 820;
}
.rw-brief-copy {
  margin: 0;
  color: var(--muted);
  line-height: 1.75;
}
.rw-source-row,
.rw-filter-row,
.rw-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.rw-source-row { margin-top: 12px; }
.rw-source-chip,
.rw-filter-chip,
.rw-tag,
.rw-meta-pill {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  gap: 6px;
  border-radius: 999px;
  padding: 5px 9px;
  font-size: 12px;
  font-weight: 720;
  white-space: nowrap;
}
.rw-source-chip {
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--muted);
}
.rw-source-chip.is-available { color: var(--green); }
.rw-source-chip.is-incomplete { color: var(--blue); }
.rw-source-chip.is-missing { color: var(--soft); text-decoration: line-through; }
.rw-filter-row {
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  margin-bottom: 12px;
}
.rw-filter-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.rw-filter-label {
  color: var(--soft);
  font-size: 12px;
  font-weight: 760;
  text-transform: uppercase;
  letter-spacing: .06em;
}
.rw-filter-chip {
  border: 1px solid var(--line-strong);
  background: var(--paper);
  color: var(--muted);
  cursor: pointer;
}
.rw-filter-chip:hover,
.rw-filter-chip.is-active {
  border-color: var(--dark);
  background: var(--dark);
  color: #fff;
}
.rw-signal-list {
  display: grid;
  gap: 10px;
}
.rw-signal-card {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
  color: var(--text);
  text-align: left;
  padding: 14px;
  cursor: pointer;
  transition: border-color .16s ease, box-shadow .16s ease, transform .16s ease;
}
.rw-signal-card:hover {
  border-color: var(--accent);
  box-shadow: 0 10px 22px rgba(45,42,38,.08);
  transform: translateY(-1px);
}
.rw-signal-card.is-active {
  border-color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent), 0 10px 22px rgba(45,42,38,.08);
}
.rw-card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 9px;
}
.rw-meta-pill {
  border: 1px solid var(--line);
  background: var(--paper-2);
  color: var(--muted);
}
.rw-meta-source { color: var(--blue); }
.rw-meta-high { color: var(--accent-dark); }
.rw-card-title {
  margin: 0;
  color: var(--dark);
  font-size: 16px;
  line-height: 1.45;
  font-weight: 820;
}
.rw-card-reason {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}
.rw-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  color: var(--soft);
  font-size: 12px;
}
.rw-locator-inline {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rw-read-label {
  color: var(--accent);
  font-weight: 820;
  white-space: nowrap;
}
.rw-detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.rw-detail-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.rw-detail-title {
  min-width: 0;
  margin: 0;
  color: var(--dark);
  font-size: 24px;
  line-height: 1.25;
  font-weight: 840;
  letter-spacing: 0;
}
.rw-detail-block {
  border-top: 1px solid var(--line);
  padding-top: 14px;
  margin-top: 14px;
}
.rw-detail-label {
  margin: 0 0 7px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 780;
  text-transform: uppercase;
  letter-spacing: .06em;
}
.rw-detail-copy {
  margin: 0;
  color: var(--text);
  line-height: 1.8;
}
.rw-excerpt {
  color: var(--text);
  line-height: 1.82;
}
.rw-excerpt p { margin: 0 0 10px; }
.rw-excerpt p:last-child { margin-bottom: 0; }
.rw-excerpt a { color: var(--accent-dark); font-weight: 720; }
.rw-excerpt strong { color: var(--dark); }
.rw-original-button {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  border: 1px solid var(--dark);
  border-radius: 8px;
  background: var(--dark);
  color: #fff;
  padding: 7px 11px;
  font-size: 12px;
  font-weight: 820;
  line-height: 1;
  text-decoration: none;
  white-space: nowrap;
}
.rw-original-button:hover {
  border-color: var(--accent-dark);
  background: var(--accent-dark);
  color: #fff;
}
.rw-empty {
  border: 1px dashed var(--line-strong);
  border-radius: 8px;
  padding: 28px;
  color: var(--muted);
  text-align: center;
  background: var(--paper);
}
.rw-bottom {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}
.rw-bottom-panel {
  min-width: 0;
  padding: 16px;
}
.rw-quality-row,
.rw-topic-row,
.rw-trend-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid var(--line);
  padding: 10px 0;
}
.rw-quality-row:first-of-type,
.rw-topic-row:first-of-type,
.rw-trend-row:first-of-type { border-top: 0; }
.rw-row-main { min-width: 0; }
.rw-row-title {
  color: var(--dark);
  font-weight: 780;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rw-row-sub {
  margin-top: 3px;
  color: var(--soft);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rw-bar-track {
  width: 88px;
  height: 8px;
  border-radius: 999px;
  background: var(--line);
  overflow: hidden;
  flex: 0 0 auto;
}
.rw-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
}
@media (max-width: 1100px) {
  .rw-header { grid-template-columns: 1fr; }
  .rw-controls { grid-template-columns: 180px minmax(220px, 1fr) auto; }
  .rw-workspace { grid-template-columns: 1fr; }
  .rw-detail-panel { position: static; }
  .rw-bottom { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .rw-page { padding: 14px; }
  .rw-controls { grid-template-columns: 1fr; }
  .rw-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .rw-filter-row { align-items: flex-start; flex-direction: column; }
  .rw-card-footer { align-items: flex-start; flex-direction: column; }
}
@media (max-width: 520px) {
  .rw-kpis { grid-template-columns: 1fr; }
  .rw-title { font-size: 32px; }
  .rw-detail-title { font-size: 21px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: .01ms !important;
  }
}
"""

_JS = r"""
(function() {
  var payload = JSON.parse(document.getElementById('dashboard-data').textContent);
  var SOURCE_KEYS = ['twitter', 'hackernews', 'producthunt'];
  var SOURCE_META = {
    twitter: { label: 'Twitter', display: 'Twitter', short: 'TW' },
    hackernews: { label: 'HackerNews', display: 'Hacker News', short: 'HN' },
    producthunt: { label: 'ProductHunt', display: 'Product Hunt', short: 'PH' }
  };
  var KIND_LABELS = {
    headline: 'Headline',
    pick: 'Pick',
    incident: 'Incident',
    tool: 'Tool',
    product: 'Product',
    account: 'Account',
    trend: 'Trend',
    metric: 'Metric',
    note: 'Note',
    summary: 'Summary'
  };
  var reportCache = {};
  var state = {
    date: (payload.dates || [])[0] || '',
    query: '',
    sourceFilter: 'all',
    kindFilter: 'all',
    selectedId: null
  };

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function(key) {
        var value = attrs[key];
        if (value === false || value == null) return;
        if (key === 'class') node.className = value;
        else if (key === 'html') node.innerHTML = value;
        else if (key === 'text') node.textContent = value;
        else if (key === 'onclick') node.addEventListener('click', value);
        else node.setAttribute(key, value === true ? '' : value);
      });
    }
    (children || []).forEach(function(child) {
      if (child == null) return;
      if (typeof child === 'string') node.appendChild(document.createTextNode(child));
      else node.appendChild(child);
    });
    return node;
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function cleanText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  function stripHtml(html) {
    var scratch = document.createElement('div');
    scratch.innerHTML = html || '';
    return cleanText(scratch.textContent || '');
  }

  function plainMarkdownToHtml(markdown) {
    return '<p>' + escapeHtml(cleanText(markdown || '')).replace(/\n/g, '<br>') + '</p>';
  }

  function truncate(value, limit) {
    value = cleanText(value);
    if (value.length <= limit) return value;
    return value.slice(0, limit - 1).trim() + '…';
  }

  function sourceMeta(sourceKey) {
    return SOURCE_META[sourceKey] || { label: sourceKey || 'Source', display: sourceKey || 'Source', short: 'SRC' };
  }

  function kindLabel(kind) {
    return KIND_LABELS[kind] || cleanText(kind || 'Note');
  }

  function priorityFor(kind) {
    if (kind === 'incident' || kind === 'headline' || kind === 'tool' || kind === 'product') return 'High';
    if (kind === 'pick' || kind === 'trend' || kind === 'metric') return 'Medium';
    return 'Low';
  }

  function slotFor(date, sourceKey) {
    return (((payload.reports_by_date || {})[date] || {})[sourceKey]) || {
      status: 'missing',
      source: sourceKey,
      date: date
    };
  }

  function isReadable(slot) {
    return slot && (slot.status === 'available' || slot.status === 'incomplete');
  }

  function locatorFrom(sourcePath, locator) {
    locator = locator || {};
    return {
      sourcePath: locator.path || sourcePath || '',
      heading: locator.heading || '',
      lineStart: locator.line_start || '',
      anchor: locator.anchor || ''
    };
  }

  function addOriginalLink(links, seen, label, url) {
    label = cleanText(label) || 'Original';
    url = cleanText(url);
    if (!/^https?:\/\//.test(url) || seen[url]) return;
    seen[url] = true;
    links.push({ label: label, url: url });
  }

  function normalizeOriginalLinks(items) {
    var links = [];
    var seen = {};
    (items || []).forEach(function(item) {
      if (!item) return;
      if (typeof item === 'string') addOriginalLink(links, seen, 'Original', item);
      else addOriginalLink(links, seen, item.label || 'Original', item.url || '');
    });
    return links;
  }

  function extractOriginalLinks(markdown, html) {
    var links = [];
    var seen = {};
    var markdownLink = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)(?:\s+"[^"]*")?\)/g;
    var match;
    while ((match = markdownLink.exec(markdown || '')) !== null) {
      addOriginalLink(links, seen, match[1], match[2]);
    }
    var scratch = document.createElement('div');
    scratch.innerHTML = html || '';
    Array.prototype.slice.call(scratch.querySelectorAll('a[href]')).forEach(function(anchor) {
      addOriginalLink(links, seen, anchor.textContent || 'Original', anchor.getAttribute('href') || '');
    });
    return links;
  }

  function buildSummaryBlock(date, sourceKey, slot) {
    var meta = sourceMeta(sourceKey);
    var locator = locatorFrom(slot.source_report_path || '', slot.source_locator || {});
    var summary = (slot.card && slot.card.summary) || slot.x_reason_no_blocks || 'No selected blocks were curated for this source.';
    var highlights = ((slot.card || {}).highlights || []).map(function(item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('');
    return {
      id: sourceKey + '-' + date + '-summary',
      sourceKey: sourceKey,
      source: meta.label,
      sourceDisplay: meta.display,
      kind: 'Summary',
      rawKind: 'summary',
      priority: 'Low',
      title: slot.title || meta.display + ' report',
      reason: summary,
      excerptHtml: '<p>' + escapeHtml(summary) + '</p>' + (highlights ? '<ul>' + highlights + '</ul>' : ''),
      excerptMarkdown: summary,
      tags: uniqueList(['Summary', meta.display, meta.label, date]),
      sourcePath: locator.sourcePath,
      heading: locator.heading || slot.title || meta.display,
      lineStart: locator.lineStart,
      anchor: locator.anchor,
      originalLinks: []
    };
  }

  function normalizeBlock(date, sourceKey, slot, block, index) {
    var meta = sourceMeta(sourceKey);
    var rawKind = block.kind || 'note';
    var label = kindLabel(rawKind);
    var locator = locatorFrom(block.source_report_path || slot.source_report_path || '', block.source_locator || {});
    var excerptHtml = block.html || plainMarkdownToHtml(block.excerpt_markdown || '');
    var excerptMarkdown = block.excerpt_markdown || stripHtml(block.html || '');
    var originalLinks = normalizeOriginalLinks(block.original_links || block.originalLinks || []);
    var originalSeen = originalLinks.reduce(function(seen, link) {
      seen[link.url] = true;
      return seen;
    }, {});
    extractOriginalLinks(excerptMarkdown, excerptHtml).forEach(function(item) {
      addOriginalLink(originalLinks, originalSeen, item.label, item.url);
    });
    return {
      id: block.id || sourceKey + '-' + date + '-' + index,
      sourceKey: sourceKey,
      source: meta.label,
      sourceDisplay: meta.display,
      kind: label,
      rawKind: rawKind,
      priority: priorityFor(rawKind),
      title: block.title || slot.title || meta.display + ' signal',
      reason: block.reason || '',
      excerptHtml: excerptHtml,
      excerptMarkdown: excerptMarkdown,
      tags: uniqueList([label, meta.display, meta.label, priorityFor(rawKind), date]),
      sourcePath: locator.sourcePath,
      heading: locator.heading || block.heading || block.title || slot.title || meta.display,
      lineStart: locator.lineStart,
      anchor: locator.anchor,
      originalLinks: originalLinks
    };
  }

  function uniqueList(values) {
    var seen = {};
    return values.filter(function(value) {
      value = cleanText(value);
      if (!value || seen[value]) return false;
      seen[value] = true;
      return true;
    });
  }

  function buildReport(date) {
    if (reportCache[date]) return reportCache[date];
    var sources = {};
    var selectedBlocks = [];
    SOURCE_KEYS.forEach(function(sourceKey) {
      var slot = slotFor(date, sourceKey);
      var meta = sourceMeta(sourceKey);
      var blocks = isReadable(slot) ? (slot.selected_blocks || []) : [];
      sources[sourceKey] = {
        key: sourceKey,
        label: meta.label,
        display: meta.display,
        available: isReadable(slot),
        status: slot.status || 'missing',
        filePath: slot.source_report_path || '',
        title: slot.title || meta.display,
        count: blocks.length,
        summary: (slot.card && slot.card.summary) || slot.x_reason_no_blocks || ''
      };
      if (!isReadable(slot)) return;
      if (!blocks.length) {
        selectedBlocks.push(buildSummaryBlock(date, sourceKey, slot));
        return;
      }
      blocks.forEach(function(block, index) {
        selectedBlocks.push(normalizeBlock(date, sourceKey, slot, block, index));
      });
    });
    reportCache[date] = {
      date: date,
      generatedAt: payload.generated_at || '',
      summary: ((payload.date_summaries || {})[date]) || '',
      sources: sources,
      selectedBlocks: selectedBlocks
    };
    return reportCache[date];
  }

  function currentReport() {
    return buildReport(state.date);
  }

  function getLocator(block) {
    if (!block || !block.sourcePath) return 'No locator';
    return block.sourcePath + (block.lineStart ? ':' + block.lineStart : '');
  }

  function formatGenerated(value) {
    if (!value) return 'Unknown';
    return value.replace('T', ' ').replace(/Z$/, ' UTC').slice(0, 19);
  }

  function matchesQuery(block, query) {
    if (!query) return true;
    var haystack = [
      block.title,
      block.reason,
      block.excerptMarkdown,
      stripHtml(block.excerptHtml),
      block.tags.join(' '),
      getLocator(block),
      block.heading,
      (block.originalLinks || []).map(function(link) { return link.label + ' ' + link.url; }).join(' ')
    ].join(' ').toLowerCase();
    return haystack.indexOf(query) !== -1;
  }

  function filteredBlocks(report) {
    var query = state.query.trim().toLowerCase();
    return report.selectedBlocks.filter(function(block) {
      var sourceOk = state.sourceFilter === 'all' || block.sourceKey === state.sourceFilter;
      var kindOk = state.kindFilter === 'all' || block.rawKind === state.kindFilter;
      return sourceOk && kindOk && matchesQuery(block, query);
    });
  }

  function selectedBlock(report, matches) {
    var blocks = matches || report.selectedBlocks;
    if (state.selectedId) {
      for (var i = 0; i < blocks.length; i++) {
        if (blocks[i].id === state.selectedId) return blocks[i];
      }
    }
    var fallback = blocks[0] || null;
    state.selectedId = fallback ? fallback.id : null;
    return fallback;
  }

  function availableSourceCount(report) {
    return SOURCE_KEYS.filter(function(key) { return report.sources[key] && report.sources[key].available; }).length;
  }

  function highPriorityCount(blocks) {
    return blocks.filter(function(block) { return block.priority === 'High'; }).length;
  }

  function kindsFor(report) {
    var seen = {};
    report.selectedBlocks.forEach(function(block) { seen[block.rawKind] = block.kind; });
    return Object.keys(seen).sort().map(function(rawKind) {
      return { rawKind: rawKind, label: seen[rawKind] };
    });
  }

  function setChildren(id, children) {
    var node = document.getElementById(id);
    node.innerHTML = '';
    children.forEach(function(child) { node.appendChild(child); });
  }

  function renderKpis(report) {
    var cards = [
      { label: 'Signals', value: String(report.selectedBlocks.length), note: 'curated readable blocks' },
      { label: 'Sources', value: availableSourceCount(report) + '/3', note: 'available source reports' },
      { label: 'High Priority', value: String(highPriorityCount(report.selectedBlocks)), note: 'incident / headline / tool / product' },
      { label: 'Generated', value: report.date ? report.date.slice(5) : '--', note: formatGenerated(report.generatedAt) }
    ];
    setChildren('kpi-row', cards.map(function(card) {
      return el('section', { class: 'rw-kpi' }, [
        el('p', { class: 'rw-kpi-label' }, [card.label]),
        el('p', { class: 'rw-kpi-value' }, [card.value]),
        el('p', { class: 'rw-kpi-note', title: card.note }, [card.note])
      ]);
    }));
  }

  function renderBrief(report) {
    var sourceChips = SOURCE_KEYS.map(function(key) {
      var source = report.sources[key];
      return el('span', {
        class: 'rw-source-chip is-' + (source.status || 'missing'),
        title: source.filePath || source.status
      }, [source.display + ' · ' + source.status]);
    });
    setChildren('daily-brief', [
      el('p', { class: 'rw-brief-title' }, ['Daily Brief']),
      el('p', { class: 'rw-brief-copy' }, [report.summary || 'No daily summary is available for this date.']),
      el('div', { class: 'rw-source-row' }, sourceChips)
    ]);
  }

  function filterButton(label, active, onClick) {
    return el('button', {
      type: 'button',
      class: 'rw-filter-chip' + (active ? ' is-active' : ''),
      'aria-pressed': active ? 'true' : 'false',
      onclick: onClick
    }, [label]);
  }

  function renderFilters(report) {
    var sourceButtons = [
      filterButton('All sources', state.sourceFilter === 'all', function() {
        state.sourceFilter = 'all';
        renderAll();
      })
    ].concat(SOURCE_KEYS.map(function(key) {
      return filterButton(sourceMeta(key).display, state.sourceFilter === key, function() {
        state.sourceFilter = key;
        renderAll();
      });
    }));
    var kindButtons = [
      filterButton('All kinds', state.kindFilter === 'all', function() {
        state.kindFilter = 'all';
        renderAll();
      })
    ].concat(kindsFor(report).map(function(kind) {
      return filterButton(kind.label, state.kindFilter === kind.rawKind, function() {
        state.kindFilter = kind.rawKind;
        renderAll();
      });
    }));
    setChildren('source-filters', sourceButtons);
    setChildren('kind-filters', kindButtons);
  }

  function renderSignalCard(block, active) {
    return el('button', {
      type: 'button',
      class: 'rw-signal-card' + (active ? ' is-active' : ''),
      onclick: function() {
        state.selectedId = block.id;
        renderAll();
        var detail = document.getElementById('detail-panel');
        if (window.matchMedia('(max-width: 1100px)').matches) {
          detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    }, [
      el('div', { class: 'rw-card-meta' }, [
        el('span', { class: 'rw-meta-pill rw-meta-source' }, [block.sourceDisplay]),
        el('span', { class: 'rw-meta-pill' }, [block.kind]),
        el('span', { class: 'rw-meta-pill' + (block.priority === 'High' ? ' rw-meta-high' : '') }, [block.priority])
      ]),
      el('h3', { class: 'rw-card-title' }, [block.title]),
      el('p', { class: 'rw-card-reason' }, [truncate(block.reason || stripHtml(block.excerptHtml), 220)]),
      el('div', { class: 'rw-card-footer' }, [
        el('span', { class: 'rw-locator-inline', title: getLocator(block) }, [getLocator(block)]),
        el('span', { class: 'rw-read-label' }, ['Read'])
      ])
    ]);
  }

  function renderSignals(report, matches, selected) {
    document.getElementById('match-count').textContent = matches.length + ' shown';
    if (!matches.length) {
      setChildren('signal-list', [
        el('div', { class: 'rw-empty' }, ['No signals match the current filters.'])
      ]);
      return;
    }
    setChildren('signal-list', matches.map(function(block) {
      return renderSignalCard(block, selected && selected.id === block.id);
    }));
  }

  function renderDetail(report, block) {
    var panel = document.getElementById('detail-panel');
    panel.innerHTML = '';
    panel.appendChild(el('div', { class: 'rw-section-head' }, [
      el('div', null, [
        el('p', { class: 'rw-section-eyebrow' }, ['Detail Panel']),
        el('h2', { class: 'rw-section-title' }, ['Reading Focus'])
      ]),
      el('span', { class: 'rw-count' }, [report.date || 'No date'])
    ]));
    if (!block) {
      panel.appendChild(el('div', { class: 'rw-empty' }, ['No readable block is available for this date.']));
      return;
    }
    panel.appendChild(el('div', { class: 'rw-detail-meta' }, [
      el('span', { class: 'rw-meta-pill rw-meta-source' }, [block.sourceDisplay]),
      el('span', { class: 'rw-meta-pill' }, [block.kind]),
      el('span', { class: 'rw-meta-pill' + (block.priority === 'High' ? ' rw-meta-high' : '') }, [block.priority])
    ]));
    var originalLinks = block.originalLinks || [];
    var titleChildren = [el('h3', { class: 'rw-detail-title' }, [block.title])];
    if (originalLinks.length) {
      titleChildren.push(el('a', {
        class: 'rw-original-button',
        href: originalLinks[0].url,
        target: '_blank',
        rel: 'noreferrer',
        title: originalLinks[0].url
      }, ['Original link']));
    }
    panel.appendChild(el('div', { class: 'rw-detail-title-row' }, titleChildren));
    panel.appendChild(el('section', { class: 'rw-detail-block' }, [
      el('p', { class: 'rw-detail-label' }, ['Why it matters']),
      el('p', { class: 'rw-detail-copy' }, [block.reason || 'No reason was provided.'])
    ]));
    panel.appendChild(el('section', { class: 'rw-detail-block' }, [
      el('p', { class: 'rw-detail-label' }, ['Full excerpt']),
      el('div', { class: 'rw-excerpt', html: block.excerptHtml || plainMarkdownToHtml(block.excerptMarkdown) })
    ]));
  }

  function sourceCoverageLines(report) {
    return SOURCE_KEYS.map(function(key) {
      var source = report.sources[key];
      return '- ' + source.display + ': ' + source.status + (source.filePath ? ' (' + source.filePath + ')' : '');
    }).join('\n');
  }

  function buildBriefMarkdown(report) {
    var lines = [
      '# Daily Brief - ' + report.date,
      '',
      '## Summary',
      report.summary || 'No summary available.',
      '',
      '## Source Coverage',
      sourceCoverageLines(report),
      '',
      '## Signals'
    ];
    if (!report.selectedBlocks.length) {
      lines.push('No curated signals.');
      return lines.join('\n');
    }
    report.selectedBlocks.forEach(function(block, index) {
      lines.push('');
      lines.push((index + 1) + '. ' + block.title);
      lines.push('   - Source: ' + block.sourceDisplay);
      lines.push('   - Kind: ' + block.kind);
      lines.push('   - Priority: ' + block.priority);
      lines.push('   - Locator: ' + getLocator(block));
      if ((block.originalLinks || []).length) {
        lines.push('   - Original link: ' + block.originalLinks.map(function(link) { return link.url; }).join(', '));
      }
      lines.push('   - Heading: ' + (block.heading || 'Unavailable'));
      lines.push('   - Reason: ' + (block.reason || 'Unavailable'));
      lines.push('   - Excerpt: ' + (stripHtml(block.excerptHtml) || block.excerptMarkdown || 'Unavailable'));
    });
    return lines.join('\n');
  }

  function downloadBrief() {
    var report = currentReport();
    var markdown = buildBriefMarkdown(report);
    var blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = 'daily-brief-' + (report.date || 'unknown') + '.md';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.setTimeout(function() { URL.revokeObjectURL(url); }, 500);
  }

  function renderSourceQuality(report) {
    var rows = SOURCE_KEYS.map(function(key) {
      var source = report.sources[key];
      var count = report.selectedBlocks.filter(function(block) { return block.sourceKey === key; }).length;
      return el('div', { class: 'rw-quality-row' }, [
        el('div', { class: 'rw-row-main' }, [
          el('div', { class: 'rw-row-title' }, [source.display]),
          el('div', { class: 'rw-row-sub', title: source.filePath || source.status }, [
            count + ' signals · ' + source.status + (source.filePath ? ' · ' + source.filePath : '')
          ])
        ]),
        el('span', { class: 'rw-count' }, [String(count)])
      ]);
    });
    setChildren('source-quality', [
      el('div', { class: 'rw-section-head' }, [
        el('div', null, [
          el('p', { class: 'rw-section-eyebrow' }, ['Source Quality']),
          el('h2', { class: 'rw-section-title' }, ['Coverage'])
        ])
      ])
    ].concat(rows));
  }

  function renderTopicRadar(report) {
    var counts = {};
    report.selectedBlocks.forEach(function(block) {
      counts[block.kind] = (counts[block.kind] || 0) + 1;
    });
    var max = Math.max.apply(null, Object.keys(counts).map(function(key) { return counts[key]; }).concat([1]));
    var rows = Object.keys(counts).sort(function(a, b) { return counts[b] - counts[a]; }).map(function(kind) {
      return el('div', { class: 'rw-topic-row' }, [
        el('div', { class: 'rw-row-main' }, [
          el('div', { class: 'rw-row-title' }, [kind]),
          el('div', { class: 'rw-row-sub' }, [counts[kind] + ' signals'])
        ]),
        el('div', { class: 'rw-bar-track', 'aria-label': kind + ' count' }, [
          el('div', { class: 'rw-bar-fill', style: 'width:' + Math.max(8, Math.round((counts[kind] / max) * 100)) + '%' })
        ])
      ]);
    });
    if (!rows.length) rows = [el('div', { class: 'rw-empty' }, ['No topic data for this date.'])];
    setChildren('topic-radar', [
      el('div', { class: 'rw-section-head' }, [
        el('div', null, [
          el('p', { class: 'rw-section-eyebrow' }, ['Topic Radar']),
          el('h2', { class: 'rw-section-title' }, ['Kinds'])
        ])
      ])
    ].concat(rows));
  }

  function renderDateTrend() {
    var dates = (payload.dates || []).slice(0, 8);
    var values = dates.map(function(date) { return buildReport(date).selectedBlocks.length; });
    var max = Math.max.apply(null, values.concat([1]));
    var rows = dates.map(function(date, index) {
      var report = buildReport(date);
      var value = values[index];
      return el('div', { class: 'rw-trend-row' }, [
        el('div', { class: 'rw-row-main' }, [
          el('div', { class: 'rw-row-title' }, [date]),
          el('div', { class: 'rw-row-sub' }, [availableSourceCount(report) + '/3 sources'])
        ]),
        el('div', { class: 'rw-bar-track', 'aria-label': date + ' signals' }, [
          el('div', { class: 'rw-bar-fill', style: 'width:' + Math.max(8, Math.round((value / max) * 100)) + '%' })
        ])
      ]);
    });
    if (!rows.length) rows = [el('div', { class: 'rw-empty' }, ['No date trend data.'])];
    setChildren('date-trend', [
      el('div', { class: 'rw-section-head' }, [
        el('div', null, [
          el('p', { class: 'rw-section-eyebrow' }, ['Date Trend']),
          el('h2', { class: 'rw-section-title' }, ['Volume'])
        ])
      ])
    ].concat(rows));
  }

  function renderBottom(report) {
    renderSourceQuality(report);
    renderTopicRadar(report);
    renderDateTrend();
  }

  function renderAll() {
    var report = currentReport();
    var matches = filteredBlocks(report);
    var selected = selectedBlock(report, matches);
    renderKpis(report);
    renderBrief(report);
    renderFilters(report);
    renderSignals(report, matches, selected);
    renderDetail(report, selected);
    renderBottom(report);
  }

  function populateDates() {
    var select = document.getElementById('date-select');
    select.innerHTML = '';
    (payload.dates || []).forEach(function(date) {
      select.appendChild(el('option', { value: date }, [date]));
    });
    select.value = state.date;
  }

  function runSmokeTests() {
    console.assert(Array.isArray(payload.dates), 'dates should be an array');
    console.assert(payload.reports_by_date && typeof payload.reports_by_date === 'object', 'reports_by_date should exist');
    console.assert(Array.isArray(payload.search_index), 'search_index should be an array');
    console.assert(typeof buildBriefMarkdown(currentReport()) === 'string', 'buildBriefMarkdown should return markdown');
    console.assert(currentReport().selectedBlocks.every(function(block) {
      return block.id && block.title && block.sourcePath !== undefined && block.lineStart !== undefined;
    }), 'selected blocks should be normalized for reading');
  }

  document.addEventListener('DOMContentLoaded', function() {
    populateDates();
    document.getElementById('date-select').addEventListener('change', function(event) {
      state.date = event.target.value;
      state.selectedId = null;
      renderAll();
    });
    document.getElementById('search-input').addEventListener('input', function(event) {
      state.query = event.target.value;
      renderAll();
    });
    document.getElementById('download-brief').addEventListener('click', downloadBrief);
    runSmokeTests();
    renderAll();
  });
})();
"""


def render_dashboard_html(model: DashboardModel) -> str:
    payload = {
        "dates": list(model.dates),
        "date_summaries": dict(model.date_summaries or {}),
        "reports_by_date": model.reports_by_date,
        "search_index": list(model.search_index),
        "generated_at": model.generated_at,
    }
    embedded = safe_json_for_script(payload)
    selected_date = model.dates[0] if model.dates else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="sources" content="Twitter · Hacker News · Product Hunt">
<link rel="icon" href="data:,">
<title>Daily Report Manager</title>
<style>{_CSS}</style>
</head>
<body>
<div class="rw-page">
  <div class="rw-shell">
    <header class="rw-header">
      <div>
        <p class="rw-kicker">Daily Report Reading Workbench</p>
        <h1 class="rw-title">日报阅读工作台</h1>
        <p class="rw-subtitle">把 Twitter、HackerNews、ProductHunt 的日报精选压成可检索、可定位、可复制的阅读流，先看信号，再读原文摘录。</p>
      </div>
      <div class="rw-controls" aria-label="Workbench controls">
        <select id="date-select" class="rw-select" aria-label="Select report date">
          <option value="{selected_date}">{selected_date}</option>
        </select>
        <div class="rw-search-wrap">
          <span class="rw-search-mark">⌕</span>
          <input id="search-input" class="rw-search" type="search" placeholder="Search title / reason / excerpt / tags" autocomplete="off">
        </div>
        <button id="download-brief" class="rw-button rw-button-primary" type="button">Download Brief</button>
      </div>
    </header>

    <section id="kpi-row" class="rw-kpis" aria-label="Reading workbench metrics"></section>

    <main class="rw-workspace">
      <section class="rw-panel" aria-label="Signal List">
        <div class="rw-section-head">
          <div>
            <p class="rw-section-eyebrow">Signal List</p>
            <h2 class="rw-section-title">Readable Blocks</h2>
          </div>
          <span id="match-count" class="rw-count">0 shown</span>
        </div>
        <section id="daily-brief" class="rw-brief" aria-label="Daily Brief"></section>
        <div class="rw-filter-row">
          <div class="rw-filter-group">
            <span class="rw-filter-label">Source</span>
            <div id="source-filters" class="rw-chip-row"></div>
          </div>
          <div class="rw-filter-group">
            <span class="rw-filter-label">Kind</span>
            <div id="kind-filters" class="rw-chip-row"></div>
          </div>
        </div>
        <div id="signal-list" class="rw-signal-list"></div>
      </section>

      <aside id="detail-panel" class="rw-detail-panel" aria-live="polite"></aside>
    </main>

    <section class="rw-bottom" aria-label="Reading workbench context">
      <section id="source-quality" class="rw-bottom-panel"></section>
      <section id="topic-radar" class="rw-bottom-panel"></section>
      <section id="date-trend" class="rw-bottom-panel"></section>
    </section>
  </div>
</div>
<script id="dashboard-data" type="application/json">{embedded}</script>
<script>{_JS}</script>
</body>
</html>
"""
