"""Infer a sensible filename for each split document.

Name = first date on the document's first page (ISO format) + the first
prominent title line(s), slugified. Falls back to document-NN.
"""

from __future__ import annotations

import re

from .features import PageFeatures, extract_dates, looks_like_page_label_line

__all__ = ["slugify", "title_for", "infer_stem", "uniquify"]

_MAX_SLUG = 60


def slugify(text: str, max_len: int = _MAX_SLUG) -> str:
    """Lowercase, alphanumerics and hyphens only, trimmed to max_len."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
        if "-" in slug:  # avoid cutting mid-word
            slug = slug.rsplit("-", 1)[0]
    return slug


def _alpha(line: str) -> str:
    return "".join(ch for ch in line if ch.isalpha())


def _titleish(line: str) -> bool:
    """Mostly-uppercase lines look like document titles."""
    alpha = _alpha(line)
    if len(alpha) < 4:
        return False
    return sum(ch.isupper() for ch in alpha) / len(alpha) >= 0.6


def _eligible(line: str) -> bool:
    stripped = line.strip()
    if not stripped or looks_like_page_label_line(stripped):
        return False
    if len(_alpha(stripped)) < 4:
        return False
    # skip lines that are essentially just a date
    if extract_dates(stripped) and len(_alpha(stripped)) <= 10:
        return False
    return True


def title_for(lines: tuple[str, ...]) -> str | None:
    """First prominent line of the page, plus a following all-caps title line."""
    candidates = [ln.strip() for ln in lines if _eligible(ln)][:6]
    if not candidates:
        return None
    parts = [candidates[0]]
    if len(candidates) > 1 and _titleish(candidates[1]):
        parts.append(candidates[1])
    return " ".join(parts)


def infer_stem(first_page: PageFeatures, ordinal: int) -> str:
    """Filename stem (no extension) for the document starting at first_page."""
    parts: list[str] = []
    if first_page.dates:
        parts.append(first_page.dates[0].isoformat())
    title = title_for(first_page.lines)
    if title:
        parts.append(slugify(title))
    stem = "-".join(p for p in parts if p)
    return stem or f"document-{ordinal:02d}"


def uniquify(stems: list[str]) -> list[str]:
    """Disambiguate duplicate stems with -2, -3, ... suffixes."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for stem in stems:
        count = seen.get(stem, 0) + 1
        seen[stem] = count
        out.append(stem if count == 1 else f"{stem}-{count}")
    return out
