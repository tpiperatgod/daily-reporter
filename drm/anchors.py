"""Shared heading normalization and anchor helpers for drm."""

from __future__ import annotations

import re
import unicodedata


def _is_decorative(ch: str) -> bool:
    return unicodedata.category(ch) in {"So", "Sk"}


def normalize_heading(heading: str) -> str:
    without_marker = re.sub(r"^\s{0,3}#{1,6}\s+", "", heading)
    without_emoji = "".join(ch for ch in without_marker if not _is_decorative(ch))
    return re.sub(r"\s+", " ", without_emoji).strip(" -—:：|")


def slugify(value: str) -> str:
    normalized = normalize_heading(value).lower()
    slug = re.sub(r"[^a-z0-9一-鿿]+", "-", normalized).strip("-")
    return slug or "section"


def make_unique_anchor(value: str, used: set[str]) -> str:
    base = slugify(value)
    candidate = base
    counter = 2
    while candidate in used:
        candidate = f"{base}-{counter}"
        counter += 1
    used.add(candidate)
    return candidate
